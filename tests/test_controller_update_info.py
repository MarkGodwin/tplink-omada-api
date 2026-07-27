"""Tests for controller update notification data."""

import pytest

from tplink_omada_client.definitions import OmadaControllerUpdateInfo


@pytest.mark.parametrize(
    ("payload_key", "release_log_key", "release_notes"),
    [
        ("hardware", "fwReleaseLog", "Hardware firmware notes."),
        ("hardware", "releaseLog", "Hardware release notes."),
        ("software", "releaseLog", "Software release notes."),
        ("software", "fwReleaseLog", "Software firmware notes."),
    ],
)
def test_controller_update_info_exposes_unified_release_notes(
    payload_key: str,
    release_log_key: str,
    release_notes: str,
) -> None:
    """Both API release-note fields are exposed as release_notes."""
    update_info = OmadaControllerUpdateInfo(
        {
            payload_key: {
                "upgrade": True,
                "currentVersion": "1.0.0",
                "latestVersion": "1.0.1",
                release_log_key: release_notes,
            }
        }
    )

    selected_update = (
        update_info.hardware
        if payload_key == "hardware"
        else update_info.software
    )

    assert selected_update is not None
    assert selected_update.upgrade is True
    assert selected_update.current_version == "1.0.0"
    assert selected_update.latest_version == "1.0.1"
    assert selected_update.release_notes == release_notes


def test_controller_update_info_exposes_only_hardware_update() -> None:
    """Hardware update payloads do not create a software update."""
    update_info = OmadaControllerUpdateInfo(
        {
            "hardware": {
                "upgrade": False,
                "currentVersion": "1.0.0",
            }
        }
    )

    assert update_info.hardware is not None
    assert update_info.software is None
    assert update_info.hardware.upgrade is False
    assert update_info.hardware.current_version == "1.0.0"
    assert update_info.hardware.latest_version == "1.0.0"
    assert update_info.hardware.release_notes is None


def test_controller_update_info_exposes_only_software_update() -> None:
    """Software update payloads do not create a hardware update."""
    update_info = OmadaControllerUpdateInfo(
        {
            "software": {
                "upgrade": False,
                "currentVersion": "6.2.10.17",
            }
        }
    )

    assert update_info.hardware is None
    assert update_info.software is not None
    assert update_info.software.upgrade is False
    assert update_info.software.current_version == "6.2.10.17"
    assert update_info.software.latest_version == "6.2.10.17"
    assert update_info.software.release_notes is None
