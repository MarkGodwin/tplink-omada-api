"""Tests for missing and null controller update sections."""

import pytest

from tplink_omada_client.definitions import (
    OmadaControllerUpdateInfo,
    OmadaHardwareUpdateInfo,
    OmadaSoftwareUpdateInfo,
)


@pytest.mark.parametrize(
    "data",
    [{}, {"hardware": None}, {"software": None}, {"hardware": None, "software": None}],
    ids=["missing", "null-hardware", "null-software", "both-null"],
)
def test_controller_update_info_reads_no_update_defaults(data):
    """Controller update info returns no normalized update when no update exists."""
    update_info = OmadaControllerUpdateInfo(data)

    assert update_info.hardware is None
    assert update_info.software is None
    assert update_info.update is None
    assert update_info.upgrade is False
    assert update_info.current_version is None
    assert update_info.latest_version is None
    assert update_info.release_notes is None
    assert update_info.release_url is None


@pytest.mark.parametrize(
    ("section", "update_type"),
    [("hardware", OmadaHardwareUpdateInfo), ("software", OmadaSoftwareUpdateInfo)],
)
@pytest.mark.parametrize("other_section", ["missing", "null", "valid"])
def test_controller_update_info_preserves_valid_sections(section, update_type, other_section):
    """Null sections do not hide valid updates or change hardware precedence."""
    hardware = {
        "upgrade": False,
        "currentVersion": "1.0.0",
        "latestVersion": "1.0.1",
        "fwReleaseLog": "Firmware notes.",
        "releaseLog": "Secondary firmware notes.",
        "releaseUrl": "https://example.com/firmware-release-notes",
        "downloadLink": "https://example.com/firmware",
    }
    software = {
        "upgrade": True,
        "currentVersion": "6.2.0",
        "latestVersion": "6.3.0",
        "releaseLog": "Software notes.",
        "fwReleaseLog": "Secondary software notes.",
        "releaseUrl": "https://example.com/software-release-notes",
        "downloadLink": "https://example.com/software",
    }
    sections = {"hardware": hardware, "software": software}
    other = "software" if section == "hardware" else "hardware"
    data = {section: sections[section]}
    if other_section == "null":
        data[other] = None
    elif other_section == "valid":
        data[other] = sections[other]

    update_info = OmadaControllerUpdateInfo(data)

    assert isinstance(getattr(update_info, section), update_type)
    assert getattr(update_info, section).raw_data == sections[section]
    if other_section != "valid":
        assert getattr(update_info, other) is None

    selected = "hardware" if data.get("hardware") is not None else "software"
    expected = sections[selected]
    expected_type = OmadaHardwareUpdateInfo if selected == "hardware" else OmadaSoftwareUpdateInfo
    assert isinstance(update_info.update, expected_type)
    assert update_info.update.raw_data == expected
    assert update_info.upgrade is expected["upgrade"]
    assert update_info.current_version == expected["currentVersion"]
    assert update_info.latest_version == expected["latestVersion"]
    assert update_info.release_notes == expected["fwReleaseLog" if selected == "hardware" else "releaseLog"]
    assert update_info.release_url == expected["releaseUrl"]
    assert update_info.update.download_link == expected["downloadLink"]


@pytest.mark.parametrize(
    ("data", "update_type"),
    [
        ({"hardware": {}}, OmadaHardwareUpdateInfo),
        ({"software": {}}, OmadaSoftwareUpdateInfo),
        ({"hardware": {}, "software": None}, OmadaHardwareUpdateInfo),
        ({"hardware": None, "software": {}}, OmadaSoftwareUpdateInfo),
        ({"hardware": {}, "software": {}}, OmadaHardwareUpdateInfo),
        ({"hardware": {}, "software": {"upgrade": True, "currentVersion": "6.2.0"}}, OmadaHardwareUpdateInfo),
    ],
)
def test_controller_update_info_preserves_empty_sections(data, update_type):
    """Empty dictionaries remain present and retain existing required-field errors."""
    update_info = OmadaControllerUpdateInfo(data)

    for section in ("hardware", "software"):
        value = getattr(update_info, section)
        if data.get(section) is None:
            assert value is None
        else:
            assert value is not None
            assert value.raw_data == data[section]

    assert isinstance(update_info.update, update_type)
    assert update_info.update.raw_data == {}
    assert update_info.release_notes is None
    assert update_info.release_url is None
    with pytest.raises(KeyError, match="upgrade"):
        _ = update_info.upgrade
