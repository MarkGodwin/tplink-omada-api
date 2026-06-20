"""Tests for the VPN CLI command."""

import argparse
import asyncio

import pytest

from tplink_omada_client import cli
from tplink_omada_client.cli import command_vpn
from tplink_omada_client.cli.config import ControllerConfig
from tplink_omada_client.vpn import OmadaVpnCategory, OmadaVpnPolicy, OmadaVpnType


def _policy(policy_id: str, name: str, status: bool = True) -> OmadaVpnPolicy:
    return OmadaVpnPolicy(
        OmadaVpnCategory.SERVER,
        {
            "id": policy_id,
            "name": name,
            "status": status,
            "vpnType": 3,
        },
    )


class FakeSiteClient:
    def __init__(self, policies: list[OmadaVpnPolicy]) -> None:
        self.policies = policies
        self.enabled_calls: list[tuple[str, bool]] = []

    async def get_vpn_policies(self) -> list[OmadaVpnPolicy]:
        return self.policies

    async def set_vpn_policy_enabled(self, policy_id: str, enabled: bool) -> None:
        self.enabled_calls.append((policy_id, enabled))
        for policy in self.policies:
            if policy.policy_id == policy_id:
                policy.raw_data["status"] = enabled


class FakeConnection:
    def __init__(self, site_client: FakeSiteClient) -> None:
        self.site_client = site_client

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get_site_client(self, site: str) -> FakeSiteClient:
        return self.site_client


def _run_command(monkeypatch, site_client: FakeSiteClient, args: dict) -> int:
    config = ControllerConfig("url", "user", "pass", "Default", True)
    monkeypatch.setattr(command_vpn, "get_target_config", lambda target: config)
    monkeypatch.setattr(command_vpn, "to_omada_connection", lambda target_config: FakeConnection(site_client))
    command_args = {
        "target": "",
        "policy": None,
        "enable": False,
        "disable": False,
        "dump": False,
    }
    command_args.update(args)
    return asyncio.run(command_vpn.command_vpn(command_args))


def test_main_registers_vpn_command(monkeypatch):
    seen = {}

    async def fake_command(args):
        seen.update(args)
        return 0

    monkeypatch.setattr(cli.command_vpn, "command_vpn", fake_command)

    assert cli.main(["vpn"]) == 0
    assert seen["policy"] is None


def test_vpn_command_lists_policies(monkeypatch, capsys):
    site_client = FakeSiteClient([_policy("policy-1", "Road warrior"), _policy("policy-2", "Site link", False)])

    assert _run_command(monkeypatch, site_client, {}) == 0

    output = capsys.readouterr().out
    assert "policy-1" in output
    assert "Road warrior" in output
    assert "\u2611" in output
    assert "policy-2" in output
    assert "Site link" in output
    assert "\u2610" in output


def test_vpn_command_enables_policy_by_name(monkeypatch, capsys):
    site_client = FakeSiteClient([_policy("policy-1", "Road warrior", False)])

    assert _run_command(monkeypatch, site_client, {"policy": "Road warrior", "enable": True}) == 0

    assert site_client.enabled_calls == [("policy-1", True)]
    output = capsys.readouterr().out
    assert "is now enabled" in output
    assert "\u2611" in output


def test_vpn_command_disables_policy_by_unique_id(monkeypatch):
    site_client = FakeSiteClient([_policy("policy-1", "Road warrior", True)])

    assert _run_command(monkeypatch, site_client, {"policy": "server_policy-1", "disable": True}) == 0

    assert site_client.enabled_calls == [("policy-1", False)]


def test_vpn_command_rejects_ambiguous_policy_name(monkeypatch):
    site_client = FakeSiteClient([_policy("policy-1", "Office"), _policy("policy-2", "Office")])

    with pytest.raises(argparse.ArgumentError, match="ambiguous"):
        _run_command(monkeypatch, site_client, {"policy": "Office", "disable": True})

    assert site_client.enabled_calls == []


def test_vpn_command_rejects_unknown_policy(monkeypatch):
    site_client = FakeSiteClient([_policy("policy-1", "Office")])

    with pytest.raises(argparse.ArgumentError, match="not found"):
        _run_command(monkeypatch, site_client, {"policy": "Missing", "enable": True})

    assert site_client.enabled_calls == []


def test_vpn_policy_uses_vpn_type_enum():
    policy = _policy("policy-1", "Office")

    assert policy.vpn_type == OmadaVpnType.OPENVPN
    assert policy.vpn_type_name == "OpenVPN"


def test_vpn_policy_handles_invalid_vpn_type():
    policy = OmadaVpnPolicy(OmadaVpnCategory.SERVER, {"id": "policy-1", "vpnType": None})

    assert policy.vpn_type == OmadaVpnType.UNKNOWN
    assert policy.vpn_type_name == "UNKNOWN"
