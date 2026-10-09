"""Tests for controller status and update notification data."""

from tplink_omada_client.definitions import (
    OmadaControllerStatus,
    OmadaControllerUpdateInfo,
    OmadaHardwareUpdateInfo,
    OmadaHardwareUpgradeStatus,
    OmadaSoftwareUpdateInfo,
)


def test_controller_status_reads_status_fields():
    """Controller status exposes the stable fields Home Assistant uses."""
    status = OmadaControllerStatus({
        "name": "  Main Controller  ",
        "macAddress": "00-11-22-33-44-55",
        "upTime": 123456,
        "controllerVersion": "6.2.10.17",
        "model": "OC200",
    })

    assert status.name == "Main Controller"
    assert status.mac == "00-11-22-33-44-55"
    assert status.uptime == 123456
    assert status.controller_version == "6.2.10.17"
    assert status.current_version == "6.2.10.17"
    assert status.model == "OC200"


def test_controller_status_uses_generic_model_fallback():
    """Missing or blank model values fall back to a generic controller model."""
    status = OmadaControllerStatus({
        "macAddress": "00-11-22-33-44-55",
        "upTime": 123456,
        "controllerVersion": "6.2.10.17",
        "model": "  ",
    })

    assert status.model == "Controller"


def test_controller_update_info_reads_hardware_update():
    """Hardware controller firmware updates remain available."""
    update_info = OmadaControllerUpdateInfo({
        "hardware": {
            "upgrade": True,
            "currentVersion": "1.0.0",
            "latestVersion": "1.0.1",
            "fwReleaseLog": "Fixed things.",
            "downloadLink": "https://example.com/firmware.bin",
        }
    })

    assert update_info.software is None
    assert update_info.hardware is not None
    assert isinstance(update_info.hardware, OmadaHardwareUpdateInfo)
    assert isinstance(update_info.update, OmadaHardwareUpdateInfo)
    assert update_info.update.raw_data == update_info.hardware.raw_data
    assert update_info.hardware.upgrade is True
    assert update_info.hardware.current_version == "1.0.0"
    assert update_info.hardware.latest_version == "1.0.1"
    assert update_info.hardware.release_notes == "Fixed things."
    assert update_info.hardware.release_url == "https://example.com/firmware.bin"
    assert update_info.current_version == "1.0.0"
    assert update_info.latest_version == "1.0.1"
    assert update_info.release_notes == "Fixed things."
    assert update_info.release_url == "https://example.com/firmware.bin"


def test_controller_update_info_reads_software_update():
    """Software controller updates are exposed when Omada returns them."""
    update_info = OmadaControllerUpdateInfo({
        "software": {
            "upgrade": True,
            "currentVersion": "6.2.10.17",
            "latestVersion": "6.2.14.6 Build 20260617091728",
            "releaseLog": "New controller software available.",
            "downloadLink": "https://example.com/software",
        }
    })

    assert update_info.hardware is None
    assert update_info.software is not None
    assert isinstance(update_info.software, OmadaSoftwareUpdateInfo)
    assert isinstance(update_info.update, OmadaSoftwareUpdateInfo)
    assert update_info.update.raw_data == update_info.software.raw_data
    assert update_info.software.upgrade is True
    assert update_info.software.current_version == "6.2.10.17"
    assert update_info.software.latest_version == "6.2.14.6 Build 20260617091728"
    assert update_info.software.release_notes == "New controller software available."
    assert update_info.software.release_url == "https://example.com/software"
    assert update_info.current_version == "6.2.10.17"
    assert update_info.latest_version == "6.2.14.6 Build 20260617091728"
    assert update_info.release_notes == "New controller software available."
    assert update_info.release_url == "https://example.com/software"


def test_controller_update_info_hardware_without_current_version():
    """Hardware controllers (e.g. OC300) may omit currentVersion from the update info."""
    update_info = OmadaControllerUpdateInfo({
        "hardware": {
            "upgrade": False,
            "latestVersion": "6.3.0.110",
        }
    })

    assert update_info.hardware is not None
    assert update_info.hardware.upgrade is False
    assert update_info.hardware.current_version is None
    assert update_info.hardware.latest_version == "6.3.0.110"
    assert update_info.current_version is None
    assert update_info.latest_version == "6.3.0.110"


def test_controller_update_info_hardware_without_any_version():
    """Missing currentVersion and latestVersion are both reported as None."""
    update_info = OmadaControllerUpdateInfo({"hardware": {"upgrade": False}})

    assert update_info.hardware is not None
    assert update_info.hardware.current_version is None
    assert update_info.hardware.latest_version is None
    assert update_info.current_version is None
    assert update_info.latest_version is None


def test_controller_update_info_software_without_current_version():
    """Software controller updates tolerate a missing currentVersion."""
    update_info = OmadaControllerUpdateInfo({
        "software": {
            "upgrade": True,
            "latestVersion": "6.2.14.6 Build 20260617091728",
        }
    })

    assert update_info.software is not None
    assert update_info.software.current_version is None
    assert update_info.software.latest_version == "6.2.14.6 Build 20260617091728"
    assert update_info.current_version is None
    assert update_info.latest_version == "6.2.14.6 Build 20260617091728"


def test_controller_update_info_reads_no_update_defaults():
    """Controller update info returns no normalized update when no update exists."""
    update_info = OmadaControllerUpdateInfo({})

    assert update_info.hardware is None
    assert update_info.software is None
    assert update_info.update is None
    assert update_info.current_version is None
    assert update_info.latest_version is None
    assert update_info.release_notes is None
    assert update_info.release_url is None


def test_hardware_upgrade_status_reads_defaults():
    """Hardware upgrade status exposes the Omada fields with stable defaults."""
    status = OmadaHardwareUpgradeStatus({"upgradeStatus": 1})

    assert status.upgrade_status == 1
    assert status.upgrade_msg == ""
    assert status.upgrade_time == 0
    assert status.download_progress == 0
    assert status.reboot_time == 300
