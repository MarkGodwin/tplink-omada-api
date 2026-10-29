"""Firmware CLI release-channel selection."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tplink_omada_client import cli
from tplink_omada_client.cli import command_firmware
from tplink_omada_client.cli.config import ControllerConfig
from tplink_omada_client.definitions import OmadaControllerUpdateInfo


def _patch_connection(monkeypatch):
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.check_firmware_updates = AsyncMock(return_value=OmadaControllerUpdateInfo({"hardware": {
        "upgrade": True, "currentVersion": "2.27.24", "latestVersion": "2.27.25",
        "releaseLog": "Controller 6.3.0.111",
    }}))
    site = MagicMock()
    site.get_devices = AsyncMock(return_value=[])
    client.get_site_client = AsyncMock(return_value=site)
    monkeypatch.setattr(command_firmware, "get_target_config", lambda target: ControllerConfig("u", "u", "p", "Default", True))
    monkeypatch.setattr(command_firmware, "to_omada_connection", lambda config: client)
    return client


@pytest.mark.parametrize("options, channel", [([], None), (["--channel", "0"], 0), (["--channel", "2"], 2)])
def test_firmware_cli_passes_channel_to_update_check(monkeypatch, capsys, options, channel):
    """The full CLI forwards the chosen channel and displays versions and release notes."""
    client = _patch_connection(monkeypatch)

    assert cli.main(["firmware", *options, "--release-notes"]) == 0

    client.check_firmware_updates.assert_awaited_once_with(channel=channel)
    client.get_site_client.assert_awaited_once_with("Default")
    output = capsys.readouterr().out
    assert "Controller Firmware" in output
    assert "2.27.24" in output
    assert "2.27.25" in output
    assert "UPDATE" in output
    assert "Controller 6.3.0.111" in output


def test_firmware_cli_rejects_noninteger_channel(monkeypatch):
    """Invalid channel syntax fails before connecting to a controller."""
    client = _patch_connection(monkeypatch)

    with pytest.raises(SystemExit) as error:
        cli.main(["firmware", "--channel", "release"])

    assert error.value.code == 2
    client.__aenter__.assert_not_awaited()


@pytest.mark.parametrize("message", [
    "Release channel selection requires Omada 6.3 or later",
    "Controller did not report release channel 0",
])
def test_firmware_cli_reports_channel_selection_errors(monkeypatch, capsys, message):
    """Unsupported channel selection exits cleanly without continuing device checks."""
    client = _patch_connection(monkeypatch)
    client.check_firmware_updates.side_effect = ValueError(message)

    assert cli.main(["firmware", "--channel", "0"]) == 1

    assert message in capsys.readouterr().out
    client.get_site_client.assert_not_awaited()
