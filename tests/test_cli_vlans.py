"""Tests for the VLAN CLI command."""

import asyncio
import copy
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from awesomeversion import AwesomeVersion

from tplink_omada_client import cli
from tplink_omada_client.cli import command_vlans
from tplink_omada_client.cli.config import ControllerConfig
from tplink_omada_client.networks import LanNetwork
from tplink_omada_client.omadasiteclient import OmadaSiteClient


class FakeSiteClient:
    def __init__(self, networks: list[LanNetwork]) -> None:
        self.networks = networks
        self.calls = 0

    async def get_lan_networks(self) -> list[LanNetwork]:
        self.calls += 1
        return self.networks


class FakeConnection:
    def __init__(self, site_client: FakeSiteClient | OmadaSiteClient) -> None:
        self.site_client = site_client

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get_site_client(self, site: str) -> FakeSiteClient | OmadaSiteClient:
        return self.site_client


def _network(name: str, vlan: int | None, subnet: str | None, dhcp_enabled: bool | None) -> LanNetwork:
    data: dict[str, Any] = {"id": f"network-{name}", "name": name, "purpose": "interface"}
    if vlan is not None:
        data["vlan"] = vlan
    if subnet is not None:
        data["gatewaySubnet"] = subnet
    if dhcp_enabled is not None:
        data["dhcpSettings"] = {"enable": dhcp_enabled}
    return LanNetwork(data)


def test_cli_loads_vlan_command_module():
    """The main CLI imports the module that owns the vlan command."""
    assert hasattr(cli, "command_vlans")


def test_main_registers_vlan_list_command(monkeypatch):
    """The main CLI dispatches the nested vlan list command."""
    async def fake_command(args):
        return 0

    monkeypatch.setattr(cli.command_vlans, "command_vlan_list", fake_command)

    assert cli.main(["vlan", "list"]) == 0


def test_vlan_list_command_prints_network_listing(monkeypatch, capsys):
    site_client = FakeSiteClient(
        [
            _network("IOT", 30, "192.168.30.1/24", True),
            _network("No DHCP", None, None, None),
        ]
    )
    monkeypatch.setattr(command_vlans, "get_target_config", lambda target: ControllerConfig("u", "u", "p", "Default", True), raising=False)
    monkeypatch.setattr(command_vlans, "to_omada_connection", lambda cfg: FakeConnection(site_client), raising=False)

    result = asyncio.run(command_vlans.command_vlan_list({"target": "", "dump": False}))

    assert result == 0
    assert site_client.calls == 1
    output = capsys.readouterr().out
    assert "Name" in output
    assert "VLAN ID" in output
    assert "Gateway subnet" in output
    assert "DHCP" in output
    assert "IOT" in output
    assert "30" in output
    assert "192.168.30.1/24" in output
    assert "enabled" in output
    assert "No DHCP" in output
    assert "-" in output


def test_vlan_list_command_dumps_raw_network_data(monkeypatch, capsys):
    site_client = FakeSiteClient([_network("IOT", 30, "192.168.30.1/24", False)])
    monkeypatch.setattr(command_vlans, "get_target_config", lambda target: ControllerConfig("u", "u", "p", "Default", True), raising=False)
    monkeypatch.setattr(command_vlans, "to_omada_connection", lambda cfg: FakeConnection(site_client), raising=False)

    assert asyncio.run(command_vlans.command_vlan_list({"target": "", "dump": True})) == 0

    output = capsys.readouterr().out
    assert "--- BEGIN RAW DATA ---" in output
    assert '"vlan": 30' in output


@pytest.fixture
def mutation_cli(monkeypatch):
    network = json.loads((Path(__file__).parent / "fixtures/vlan_management.json").read_text())["network"]
    state = []
    api = MagicMock()
    api.get_controller_version = AsyncMock(return_value=AwesomeVersion("6.2.0.0"))
    api.format_url.side_effect = lambda path, site: f"/{site}/{path}"
    site = OmadaSiteClient("example-site", api)

    async def inventory():
        return [LanNetwork(copy.deepcopy(n)) for n in state]

    async def write(method: str, url: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        if method == "post":
            assert json is not None
            item = copy.deepcopy(network)
            item.update({k: v for k, v in json.items() if k != "vlans"})
            item["vlan"] = int(json["vlans"])
            state.append(item)
        elif method == "patch":
            assert json is not None
            state[0].update(copy.deepcopy(json))
        elif method == "delete":
            state.clear()
        return {"errorCode": 0, "msg": "OK"}

    site.get_lan_networks = inventory
    api.request = AsyncMock(side_effect=write)
    monkeypatch.setattr(command_vlans, "get_target_config", lambda _: ControllerConfig("u", "u", "p", "Default", True))
    monkeypatch.setattr(command_vlans, "to_omada_connection", lambda _: FakeConnection(site))
    return state, network, api


@pytest.mark.parametrize("operation", ["create", "modify", "delete"])
@pytest.mark.parametrize("apply", [False, True])
def test_vlan_cli_preview_and_explicit_apply_use_guarded_api(mutation_cli, capsys, operation, apply):
    state, network, api = mutation_cli
    if operation == "create":
        args = ["vlan", "create", "--name", "example-vlan", "--vlan-id", "3990"]
    else:
        state.append(copy.deepcopy(network))
        args = ["vlan", operation, network["id"]]
        if operation == "modify":
            args += ["--name", "renamed"]
    if apply:
        args += ["--apply"]
    assert cli.main(args) == 0
    output = capsys.readouterr().out
    assert "example-vlan" in output
    if apply:
        assert "Verified" in output
        assert api.request.await_count == 1
        if operation == "create":
            assert state[0]["vlan"] == 3990
        elif operation == "modify":
            assert state[0]["name"] == "renamed"
        else:
            assert state == []
    else:
        assert "Preview" in output and "--apply" in output
        api.request.assert_not_awaited()
    if operation == "delete":
        assert "WARNING" in output


@pytest.mark.parametrize("args", [["create", "--name", "x", "--vlan-id", "4091"], ["modify", "example-network-id"], ["delete", "missing"]])
def test_vlan_cli_validation_errors_return_failure_without_writing(mutation_cli, capsys, args):
    _, _, api = mutation_cli
    assert cli.main(["vlan", *args, "--apply"]) == 1
    assert capsys.readouterr().err
    api.request.assert_not_awaited()


def test_vlan_cli_apply_controller_error_does_not_claim_success(mutation_cli, capsys):
    from tplink_omada_client.exceptions import RequestFailed

    _, _, api = mutation_cli
    api.request.side_effect = RequestFailed(-1001, "controller rejection")
    assert cli.main(["vlan", "create", "--name", "x", "--vlan-id", "20", "--apply"]) == 1
    captured = capsys.readouterr()
    assert "controller rejection" in captured.err
    assert "Verified" not in captured.out


def test_vlan_cli_rejects_routed_delete_even_with_apply(mutation_cli):
    state, network, api = mutation_cli
    state.append(network | {"purpose": "interface"})
    assert cli.main(["vlan", "delete", network["id"], "--apply"]) == 1
    api.request.assert_not_awaited()


def test_vlan_list_includes_network_id_for_dhcp_usage(monkeypatch, capsys):
    site = FakeSiteClient([_network("IOT", 30, None, False)])
    monkeypatch.setattr(command_vlans, "get_target_config", lambda _: ControllerConfig("u", "u", "p", "Default", True))
    monkeypatch.setattr(command_vlans, "to_omada_connection", lambda _: FakeConnection(site))
    assert asyncio.run(command_vlans.command_vlan_list({"target": "", "dump": False})) == 0
    assert "network-IOT" in capsys.readouterr().out


def test_vlan_cli_rejects_unknown_operation_without_deleting(mutation_cli):
    state, network, api = mutation_cli
    state.append(copy.deepcopy(network))
    args = {"vlan_command": "unknown", "network": network["id"], "target": "", "apply": True}
    assert asyncio.run(command_vlans.command_vlan_mutation(args)) == 1
    assert len(state) == 1
    api.request.assert_not_awaited()


@pytest.mark.parametrize("operation", ["modify", "delete"])
def test_vlan_cli_apply_does_not_reinterpret_a_vanished_id_as_a_name(mutation_cli, capsys, operation):
    state, network, api = mutation_cli
    state.append(copy.deepcopy(network))
    replacement = network | {"id": "replacement-id", "name": network["id"], "vlan": 20}
    config = command_vlans.get_target_config("")
    connection = command_vlans.to_omada_connection(config)
    site = asyncio.run(connection.get_site_client("Default"))
    reads = 0

    async def inventory():
        nonlocal reads
        reads += 1
        if reads == 2:
            state[:] = [copy.deepcopy(replacement)]
        return [LanNetwork(copy.deepcopy(n)) for n in state]

    site.get_lan_networks = inventory
    args = ["vlan", operation, network["name"], "--apply"]
    if operation == "modify":
        args += ["--name", "renamed"]
    assert cli.main(args) == 1
    assert state == [replacement]
    api.request.assert_not_awaited()
    captured = capsys.readouterr()
    assert captured.err
    assert "Verified" not in captured.out
