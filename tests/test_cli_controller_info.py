"""Tests for the controller-info CLI command."""

import asyncio

from tplink_omada_client import cli
from tplink_omada_client.cli import command_controller_info
from tplink_omada_client.cli.config import ControllerConfig
from tplink_omada_client.definitions import OmadaControllerInfo, OmadaControllerStatus, OmadaControllerType


def _controller_info_data() -> dict:
    return {
        "controllerVer": "6.2.10.17",
        "apiVer": "5",
        "configured": True,
        "type": 2,
        "supportApp": True,
        "omadacId": "controller-id",
        "registeredRoot": True,
        "omadacCategory": "Software",
        "mspMode": False,
        "omadaCloudUrl": "https://omada.tplinkcloud.com",
    }


def _controller_status_data(model: str | None = "OC200", name: str | None = "Main Controller") -> dict:
    data = {
        "name": name,
        "macAddress": "00-11-22-33-44-55",
        "upTime": 123456,
        "controllerVersion": "6.2.10.17",
    }
    if model is not None:
        data["model"] = model
    return data


class FakeConnection:
    """Controller API stand-in for controller-info CLI tests."""

    def __init__(
        self,
        info_data: dict | None = None,
        type_data: dict | None = None,
        status_data: dict | None = None,
        legacy_name: str = "Legacy Controller",
    ) -> None:
        self.info = OmadaControllerInfo(info_data or _controller_info_data())
        self.controller_type = OmadaControllerType(type_data or {"isSoftController": True})
        self.status = OmadaControllerStatus(status_data or _controller_status_data())
        self.legacy_name = legacy_name
        self.legacy_name_requested = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get_controller_info(self) -> OmadaControllerInfo:
        return self.info

    async def get_controller_type(self) -> OmadaControllerType:
        return self.controller_type

    async def get_controller_status(self) -> OmadaControllerStatus:
        return self.status

    async def get_controller_name(self) -> str:
        self.legacy_name_requested = True
        return self.legacy_name


def _patch_connection(monkeypatch, connection: FakeConnection) -> None:
    monkeypatch.setattr(
        command_controller_info,
        "get_target_config",
        lambda target: ControllerConfig("u", "u", "p", "Default", True),
    )
    monkeypatch.setattr(command_controller_info, "to_omada_connection", lambda cfg: connection)


def test_main_registers_controller_info_command(monkeypatch):
    seen = {}

    async def fake_command(args):
        seen.update(args)
        return 0

    monkeypatch.setattr(cli.command_controller_info, "command_controller_info", fake_command)

    assert cli.main(["controller-info"]) == 0
    assert seen["dump"] is False


def test_controller_info_outputs_software_controller_details(monkeypatch, capsys):
    connection = FakeConnection(type_data={"isSoftController": True, "combinedGateway": False})
    _patch_connection(monkeypatch, connection)

    result = asyncio.run(command_controller_info.command_controller_info({"target": "", "dump": False}))

    assert result == 0
    output = capsys.readouterr().out
    assert "Controller name: Main Controller" in output
    assert "Controller version: 6.2.10.17" in output
    assert "API version: 5" in output
    assert "Controller type: 2" in output
    assert "Software Controller: True" in output
    assert "Combined gateway: False" in output
    assert "Controller MAC: 00-11-22-33-44-55" in output
    assert "Controller uptime: 123456" in output
    assert "Controller model: OC200" in output
    assert "Controller category: Software" in output
    assert "Configured: True" in output
    assert "Root registered: True" in output
    assert "Supports Omada app: True" in output
    assert "MSP mode: False" in output
    assert "Omada cloud URL: https://omada.tplinkcloud.com" in output
    assert connection.legacy_name_requested is False


def test_controller_info_outputs_hardware_controller_indication(monkeypatch, capsys):
    connection = FakeConnection(
        type_data={"isSoftController": False, "combinedGateway": True},
        status_data=_controller_status_data(model="OC300"),
    )
    _patch_connection(monkeypatch, connection)

    result = asyncio.run(command_controller_info.command_controller_info({"target": "", "dump": False}))

    assert result == 0
    output = capsys.readouterr().out
    assert "Software Controller: False" in output
    assert "Combined gateway: True" in output
    assert "Controller model: OC300" in output


def test_controller_info_does_not_show_generic_model_fallback(monkeypatch, capsys):
    connection = FakeConnection(status_data=_controller_status_data(model="  "))
    _patch_connection(monkeypatch, connection)

    result = asyncio.run(command_controller_info.command_controller_info({"target": "", "dump": False}))

    assert result == 0
    assert "Controller model: Unknown" in capsys.readouterr().out


def test_controller_info_falls_back_to_legacy_name_endpoint(monkeypatch, capsys):
    connection = FakeConnection(status_data=_controller_status_data(name="  "), legacy_name="Legacy Name")
    _patch_connection(monkeypatch, connection)

    result = asyncio.run(command_controller_info.command_controller_info({"target": "", "dump": False}))

    assert result == 0
    assert "Controller name: Legacy Name" in capsys.readouterr().out
    assert connection.legacy_name_requested is True


def test_controller_info_dump_outputs_separate_raw_payloads(monkeypatch, capsys):
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)

    result = asyncio.run(command_controller_info.command_controller_info({"target": "", "dump": True}))

    assert result == 0
    output = capsys.readouterr().out
    assert output.count("--- BEGIN RAW DATA ---") == 3
    assert '"controllerVer": "6.2.10.17"' in output
    assert '"isSoftController": true' in output
    assert '"macAddress": "00-11-22-33-44-55"' in output
