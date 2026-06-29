"""Tests for controller update notification data."""

from tplink_omada_client.definitions import OmadaControllerUpdateInfo


def test_controller_update_info_reads_hardware_update():
    """Hardware controller firmware updates remain available."""
    update_info = OmadaControllerUpdateInfo({
        "hardware": {
            "upgrade": True,
            "currentVersion": "1.0.0",
            "latestVersion": "1.0.1",
            "fwReleaseLog": "Fixed things.",
        }
    })

    assert update_info.software is None
    assert update_info.hardware is not None
    assert update_info.hardware.upgrade is True
    assert update_info.hardware.current_version == "1.0.0"
    assert update_info.hardware.latest_version == "1.0.1"
    assert update_info.hardware.release_notes == "Fixed things."


def test_controller_update_info_reads_software_update():
    """Software controller updates are exposed when Omada returns them."""
    update_info = OmadaControllerUpdateInfo({
        "software": {
            "upgrade": True,
            "currentVersion": "6.2.10.17",
            "latestVersion": "6.2.14.6 Build 20260617091728",
            "releaseLog": "New controller software available.",
        }
    })

    assert update_info.hardware is None
    assert update_info.software is not None
    assert update_info.software.upgrade is True
    assert update_info.software.current_version == "6.2.10.17"
    assert update_info.software.latest_version == "6.2.14.6 Build 20260617091728"
    assert update_info.software.release_notes == "New controller software available."
