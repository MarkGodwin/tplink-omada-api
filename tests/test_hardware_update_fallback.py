"""Tests for Omada 6.3 hardware release-channel updates."""

# pylint: disable=protected-access

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from awesomeversion import AwesomeVersion

from tplink_omada_client.exceptions import ConnectionFailed, LoginFailed, RequestFailed
from tplink_omada_client.omadaapiconnection import OmadaApiConnection
from tplink_omada_client.omadaclient import OmadaClient


def _client(responses, version="6.3.0.110"):
    api = Mock(spec=OmadaApiConnection)
    api.format_url.side_effect = lambda endpoint: f"api/v2/{endpoint}"
    api.get_controller_version = AsyncMock(return_value=AwesomeVersion(version))
    api.request = AsyncMock(side_effect=responses)
    client = OmadaClient("https://omada.example", "user", "pass")
    client._api = api
    return client, api


def test_oc200_without_update_returns_installed_firmware_version():
    """OC200 channel 2 must not expose the update available on channel 0."""
    firmware = "2.27.24 Build 20260924 Rel.15471"
    client, api = _client([
        {"isSoftController": False},
        {"currentChannel": 2, "controllerChannel": 2, "currentControllerVer": "6.3.0.110",
         "upgradeList": [
             {"channel": 0, "update": True, "latestVersion": "2.27.25 Build 20261013 Rel.29795"},
             {"channel": 1, "update": False}, {"channel": 2, "update": False},
         ]},
        {"upgrade": False, "currentVersion": firmware, "denyUpgrade": False},
    ])

    info = asyncio.run(client.check_firmware_updates())

    assert info.hardware is not None
    assert info.software is None
    assert info.current_version == info.latest_version == firmware
    assert info.upgrade is False
    assert api.request.await_args_list == [
        (("get", "api/v2/anon/controllerType"),),
        (("get", "api/v2/maintenance/software/channelUpdate"),),
        (("get", "api/v2/maintenance/hardware/checkFirmware"),),
    ]


@pytest.mark.parametrize("channel", [0, 1, 2])
def test_available_update_preserves_firmware_metadata(channel):
    """Selected-channel updates use firmware versions and preserve metadata."""
    client, _ = _client([
        {"isSoftController": False},
        {"currentChannel": channel, "currentControllerVer": "6.3.0.110", "upgradeList": [
            {"channel": channel, "update": True, "latestVersion": "2.27.25",
             "releaseLog": "Firmware fixes", "releaseUrl": "https://example.com/notes",
             "downloadUrl": "https://example.com/firmware.bin", "denyUpgrade": False},
        ]},
        {"upgrade": False, "currentVersion": "2.27.24"},
    ])

    info = asyncio.run(client.check_firmware_updates())

    assert info.upgrade is True
    assert info.current_version == "2.27.24"
    assert info.latest_version == "2.27.25"
    assert info.release_notes == "Firmware fixes"
    assert info.release_url == "https://example.com/notes"
    assert info.hardware.download_link == "https://example.com/firmware.bin"


@pytest.mark.parametrize("channel_data", [{}, {"currentChannel": 2, "upgradeList": [
    {"channel": 0, "update": True, "latestVersion": "2.27.25"},
]}])
def test_missing_selected_channel_returns_empty_update(channel_data):
    """A missing selected channel cannot expose another channel's update."""
    client, api = _client([{"isSoftController": False}, channel_data])

    info = asyncio.run(client.check_firmware_updates())

    assert info.update is None
    assert api.request.await_count == 2


@pytest.mark.parametrize("version", ["5.15.24", "6.2.10.17"])
def test_older_hardware_notifications_are_preserved(version):
    """Older hardware keeps its original notification behavior."""
    notification = {"hardware": {"upgrade": False}}
    client, api = _client([notification], version)

    info = asyncio.run(client.check_firmware_updates())

    assert info.raw_data == notification
    assert api.request.await_count == 1


@pytest.mark.parametrize("endpoint", ["channel", "firmware"])
@pytest.mark.parametrize("error", [RequestFailed(403, "Forbidden"), LoginFailed(-30109, "Login failed"), ConnectionFailed()])
def test_hardware_check_errors_propagate(error, endpoint):
    """Failed firmware checks must not be presented as successful no-update checks."""
    responses = [{"isSoftController": False}]
    if endpoint == "firmware":
        responses.append({"currentChannel": 2, "upgradeList": [{"channel": 2, "update": False}]})
    client, _ = _client([*responses, error])

    with pytest.raises(type(error)):
        asyncio.run(client.check_firmware_updates())
