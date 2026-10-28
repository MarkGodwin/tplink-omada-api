"""Tests for Omada 6.3 software controller release-channel updates."""

# pylint: disable=protected-access

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from awesomeversion import AwesomeVersion

from tplink_omada_client.exceptions import ConnectionFailed, LoginFailed, RequestFailed
from tplink_omada_client.omadaapiconnection import OmadaApiConnection
from tplink_omada_client.omadaclient import OmadaClient


def _client(responses, version="6.3.0.45"):
    api = Mock(spec=OmadaApiConnection)
    api.format_url.side_effect = lambda endpoint: f"api/v2/{endpoint}"
    api.get_controller_version = AsyncMock(return_value=AwesomeVersion(version))
    api.request = AsyncMock(side_effect=responses)
    client = OmadaClient("https://omada.example", "user", "pass")
    client._api = api
    return client, api


@pytest.mark.parametrize("channel", [0, 1], ids=["stable", "beta"])
def test_software_update_uses_selected_release_channel(channel):
    """Modern controllers use the selected channel directly, regardless of list order."""
    selected = {
        "channel": channel,
        "update": True,
        "latestVersion": "6.3.0.111 Build 20261009150935",
        "releaseLog": "Controller fixes.",
        "releaseUrl": "https://example.com/release-notes",
        "downloadUrl": "https://example.com/controller.deb",
        "denyUpgrade": False,
    }
    client, api = _client([
        {"isSoftController": True},
        {
            "currentControllerVer": "6.3.0.45",
            "currentChannel": channel,
            "upgradeList": [{"channel": 1 - channel, "update": False}, selected],
        },
    ])

    update = asyncio.run(client.check_firmware_updates())

    assert update.hardware is None
    assert update.software is not None
    assert update.upgrade is True
    assert update.current_version == "6.3.0.45"
    assert update.latest_version == "6.3.0.111 Build 20261009150935"
    assert update.release_notes == "Controller fixes."
    assert update.release_url == "https://example.com/release-notes"
    assert update.software.download_link == "https://example.com/controller.deb"
    assert api.request.await_args_list == [
        (("get", "api/v2/anon/controllerType"),),
        (("get", "api/v2/maintenance/software/channelUpdate"),),
    ]


@pytest.mark.parametrize("extra", [{}, {"latestVersion": "6.3.0.111 Build 20261009150935"}])
def test_software_without_update_reports_current_version(extra):
    """An update on another channel or an installed build must not create a false update."""
    client, _ = _client([
        {"isSoftController": True},
        {
            "currentControllerVer": "6.3.0.111",
            "currentChannel": 0,
            "upgradeList": [
                {"channel": 1, "update": True, "latestVersion": "6.4.0.1"},
                {"channel": 0, "update": False, "denyUpgrade": False, **extra},
            ],
        },
    ], version="6.3.0.111")

    update = asyncio.run(client.check_firmware_updates())

    assert update.software is not None
    assert update.upgrade is False
    assert update.current_version == update.latest_version == "6.3.0.111"
    assert update.release_notes is None
    assert update.release_url is None
    assert update.software.download_link is None


@pytest.mark.parametrize("channel_data", [{}, {"currentChannel": 0, "upgradeList": []}, {
    "currentChannel": 0, "upgradeList": [{"channel": 1, "update": True, "latestVersion": "6.4.0.1"}],
}])
def test_missing_selected_channel_keeps_empty_update(channel_data):
    """Missing channel data must not select a different channel or invent an update."""
    client, _ = _client([{"isSoftController": True}, channel_data])

    update = asyncio.run(client.check_firmware_updates())

    assert update.update is None
    assert update.upgrade is False


@pytest.mark.parametrize("version", ["5.15.24", "6.2.10.17"])
def test_older_controllers_do_not_query_release_channels(version):
    """Controllers before 6.3 keep the existing empty-notification behavior."""
    client, api = _client([{}], version=version)

    update = asyncio.run(client.check_firmware_updates())

    assert update.update is None
    assert api.request.await_count == 1


def test_hardware_uses_shared_channel_endpoint():
    """Hardware controllers also use software/channelUpdate on 6.3."""
    client, api = _client([
        {"isSoftController": False},
        {"currentChannel": 2, "currentControllerVer": "6.3.0.110",
         "upgradeList": [{"channel": 2, "update": False}]},
        {"currentVersion": "2.27.24"},
    ])

    update = asyncio.run(client.check_firmware_updates())

    assert update.hardware is not None
    assert update.software is None
    assert update.current_version == update.latest_version == "2.27.24"
    assert api.request.await_count == 3


@pytest.mark.parametrize("section", ["hardware", "software"])
def test_existing_notifications_are_preserved(section):
    """Valid notifications continue to use their existing data without extra requests."""
    legacy = {section: {"upgrade": True, "currentVersion": "6.3.0.45", "latestVersion": "6.3.0.111"}}
    client, api = _client([legacy], version="6.2.10.17")

    update = asyncio.run(client.check_firmware_updates())

    assert update.raw_data == legacy
    assert update.upgrade is True
    assert update.latest_version == "6.3.0.111"
    assert api.request.await_count == 1
    api.get_controller_version.assert_awaited_once()


@pytest.mark.parametrize("error", [RequestFailed(403, "Forbidden"), LoginFailed(-30109, "Login failed"), ConnectionFailed()])
def test_channel_request_errors_propagate(error):
    """Authentication, permission and connection failures must not appear as no update."""
    client, _ = _client([{"isSoftController": True}, error])

    with pytest.raises(type(error)):
        asyncio.run(client.check_firmware_updates())
