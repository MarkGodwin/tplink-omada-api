"""Controller firmware CLI previews, installation, and rejected updates."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tplink_omada_client import cli
from tplink_omada_client.cli import command_controller_firmware_update as command
from tplink_omada_client.cli.config import ControllerConfig
from tplink_omada_client.definitions import OmadaControllerType, OmadaControllerUpdateInfo
from tplink_omada_client.exceptions import ConnectionFailed, RequestFailed

CURRENT = "2.27.24 Build 20260924 Rel.15471"
LATEST = "2.27.25 Build 20261013 Rel.29795"


def _connection(monkeypatch, data=None):
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_controller_type = AsyncMock(return_value=OmadaControllerType({"isSoftController": False}))
    client.check_firmware_updates = AsyncMock(return_value=OmadaControllerUpdateInfo(data if data is not None else {
        "hardware": {"upgrade": True, "currentVersion": CURRENT, "latestVersion": LATEST,
                     "releaseLog": "Controller 6.3.0.111", "denyUpgrade": False},
    }))
    client.install_controller_firmware = AsyncMock(return_value=True)
    monkeypatch.setattr(command, "get_target_config", lambda target: ControllerConfig("u", "u", "p", "Default", True))
    monkeypatch.setattr(command, "to_omada_connection", lambda config: client)
    return client


@pytest.mark.parametrize("options, channel", [([], None), (["--channel", "0"], 0)])
def test_preview_does_not_install(monkeypatch, capsys, options, channel):
    """Preview shows the exact firmware and release notes without submitting an upgrade."""
    client = _connection(monkeypatch)

    assert cli.main(["-t", "OC200", "controller-firmware-update", *options, "--release-notes"]) == 0

    client.check_firmware_updates.assert_awaited_once_with(channel=channel)
    client.install_controller_firmware.assert_not_awaited()
    output = capsys.readouterr().out
    assert f"{CURRENT} -> {LATEST}" in output
    assert "Controller 6.3.0.111" in output
    assert "Preview only" in output
    assert "--apply" in output


def test_apply_installs_exact_selected_firmware_version(monkeypatch, capsys):
    """An applied release-channel update passes the complete firmware version to the API."""
    client = _connection(monkeypatch)

    assert cli.main(["controller-firmware-update", "--channel", "0", "--apply"]) == 0

    client.check_firmware_updates.assert_awaited_once_with(channel=0)
    client.install_controller_firmware.assert_awaited_once_with(LATEST)
    output = capsys.readouterr().out
    assert "request accepted" in output
    assert "restart" in output
    assert "Preview only" not in output


def test_software_controller_cannot_install(monkeypatch, capsys):
    """Hardware upgrade commands must not be sent to software controllers."""
    client = _connection(monkeypatch)
    client.get_controller_type.return_value = OmadaControllerType({"isSoftController": True})

    assert cli.main(["controller-firmware-update", "--apply"]) == 1

    client.check_firmware_updates.assert_not_awaited()
    client.install_controller_firmware.assert_not_awaited()
    assert "only for hardware controllers" in capsys.readouterr().out


@pytest.mark.parametrize("data, code, message", [
    ({}, 1, "did not report hardware"),
    ({"hardware": {"upgrade": False}}, 0, "No controller firmware update"),
    ({"hardware": {"upgrade": True, "denyUpgrade": True, "latestVersion": LATEST}}, 1, "prohibits"),
    ({"hardware": {"upgrade": True}}, 1, "usable target firmware version"),
    ({"hardware": {"upgrade": True, "latestVersion": None}}, 1, "usable target firmware version"),
    ({"hardware": {"upgrade": True, "latestVersion": " "}}, 1, "usable target firmware version"),
    ({"hardware": {"upgrade": True, "currentVersion": CURRENT, "latestVersion": CURRENT}}, 1, "usable target firmware version"),
])
def test_unavailable_or_invalid_update_does_not_install(monkeypatch, capsys, data, code, message):
    """Missing, disallowed, and unusable targets cannot trigger firmware installation."""
    client = _connection(monkeypatch, data)

    assert cli.main(["controller-firmware-update", "--apply"]) == code

    client.install_controller_firmware.assert_not_awaited()
    assert message in capsys.readouterr().out


@pytest.mark.parametrize("method", ["check_firmware_updates", "install_controller_firmware"])
@pytest.mark.parametrize("error", [ValueError("Unknown channel"), RequestFailed(403, "Forbidden"), ConnectionFailed()])
def test_failures_exit_without_claiming_success(monkeypatch, capsys, method, error):
    """Selection and request failures produce a nonzero exit and no success message."""
    client = _connection(monkeypatch)
    getattr(client, method).side_effect = error

    assert cli.main(["controller-firmware-update", "--apply"]) == 1

    output = capsys.readouterr().out
    assert "request failed" in output
    assert "request accepted" not in output
    if method == "check_firmware_updates":
        client.install_controller_firmware.assert_not_awaited()
    else:
        client.install_controller_firmware.assert_awaited_once_with(LATEST)


def test_rejected_install_does_not_claim_success(monkeypatch, capsys):
    """An API method returning false must not be reported as an accepted upgrade."""
    client = _connection(monkeypatch)
    client.install_controller_firmware.return_value = False

    assert cli.main(["controller-firmware-update", "--apply"]) == 1

    assert "not accepted" in capsys.readouterr().out
