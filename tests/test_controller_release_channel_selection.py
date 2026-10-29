"""Explicit release-channel selection must not change controller settings."""

# pylint: disable=protected-access

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from awesomeversion import AwesomeVersion

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


@pytest.mark.parametrize("hardware", [False, True], ids=["software", "hardware"])
@pytest.mark.parametrize("channel", [None, 0])
def test_explicit_release_channel_exposes_update_without_changing_configuration(hardware, channel):
    """The release channel can offer an update while configured channel 2 has none."""
    current = "2.27.24" if hardware else "6.3.0.110"
    latest = "2.27.25" if hardware else "6.3.0.111"
    responses = [
        {"isSoftController": not hardware},
        {"currentChannel": 2, "controllerChannel": 2, "currentControllerVer": "6.3.0.110", "upgradeList": [
            {"channel": 2, "update": False},
            {"channel": 0, "update": True, "latestVersion": latest,
             "downloadUrl": "https://example.com/update", "releaseLog": "Controller 6.3.0.111"},
        ]},
    ]
    if hardware:
        responses.append({"upgrade": False, "currentVersion": current})
    client, api = _client(responses)

    info = asyncio.run(client.check_firmware_updates(channel=channel))

    assert info.current_version == current
    assert info.latest_version == (latest if channel == 0 else current)
    assert info.upgrade is (channel == 0)
    assert info.release_notes == ("Controller 6.3.0.111" if channel == 0 else None)
    assert info.update.download_link == ("https://example.com/update" if channel == 0 else None)
    assert (info.hardware is not None) is hardware
    assert all(call.args[0] == "get" for call in api.request.await_args_list)


def test_missing_explicit_channel_raises_instead_of_using_another_channel():
    """An unsupported requested channel is an error rather than a no-update result."""
    client, api = _client([
        {"isSoftController": False},
        {"currentChannel": 2, "upgradeList": [{"channel": 2, "update": False}]},
    ])

    with pytest.raises(ValueError, match="did not report release channel 0"):
        asyncio.run(client.check_firmware_updates(channel=0))

    assert api.request.await_count == 2


def test_older_controller_rejects_explicit_channel():
    """Older controllers must not silently ignore an explicit channel selection."""
    client, api = _client([{"hardware": {"upgrade": False}}], version="6.2.10.17")

    with pytest.raises(ValueError, match="requires Omada 6.3"):
        asyncio.run(client.check_firmware_updates(channel=0))

    api.request.assert_not_awaited()
