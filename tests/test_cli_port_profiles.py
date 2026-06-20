"""Tests for the port_profiles CLI command."""

import argparse
import asyncio

import pytest

from tplink_omada_client import cli
from tplink_omada_client.cli import command_port_profiles
from tplink_omada_client.cli.config import ControllerConfig
from tplink_omada_client.devices import OmadaPortProfile


def _profile(profile_id: str, name: str, dot1x: int = 2) -> OmadaPortProfile:
    return OmadaPortProfile(
        {
            "id": profile_id,
            "name": name,
            "type": 2,
            "poe": 2,
            "dot1x": dot1x,
            "portIsolationEnable": False,
            "lldpMedEnable": True,
            "bandWidthCtrlType": 0,
            "spanningTreeEnable": False,
            "loopbackDetectEnable": True,
            "eeeEnable": False,
            "flowControlEnable": False,
            "loopbackDetectVlanBasedEnable": False,
        }
    )


class FakeSiteClient:
    def __init__(self, profiles: list[OmadaPortProfile]) -> None:
        self.profiles = profiles

    async def get_port_profiles(self) -> list[OmadaPortProfile]:
        return self.profiles


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
    monkeypatch.setattr(command_port_profiles, "get_target_config", lambda target: config)
    monkeypatch.setattr(command_port_profiles, "to_omada_connection", lambda target_config: FakeConnection(site_client))
    command_args = {
        "target": "",
        "profile": None,
        "dump": False,
    }
    command_args.update(args)
    return asyncio.run(command_port_profiles.command_port_profiles(command_args))


def test_main_registers_port_profiles_command(monkeypatch):
    seen = {}

    async def fake_command(args):
        seen.update(args)
        return 0

    monkeypatch.setattr(cli.command_port_profiles, "command_port_profiles", fake_command)

    assert cli.main(["port_profiles"]) == 0
    assert seen["profile"] is None


def test_port_profiles_command_lists_profiles(monkeypatch, capsys):
    site_client = FakeSiteClient([_profile("profile-1", "Default"), _profile("profile-2", "Camera")])

    assert _run_command(monkeypatch, site_client, {}) == 0

    output = capsys.readouterr().out
    assert "profile-1" in output
    assert "Default" in output
    assert "USE_DEVICE_SETTINGS" in output
    assert "profile-2" in output
    assert "Camera" in output


def test_port_profiles_command_views_profile_by_name(monkeypatch, capsys):
    site_client = FakeSiteClient([_profile("profile-1", "Default")])

    assert _run_command(monkeypatch, site_client, {"profile": "Default"}) == 0

    output = capsys.readouterr().out
    assert "Port Profile: Default" in output
    assert "profile-1" in output
    assert "802.1X" in output
    assert "AUTO" in output
    assert "LLDP-MED" in output


def test_port_profiles_command_rejects_ambiguous_profile_name(monkeypatch):
    site_client = FakeSiteClient([_profile("profile-1", "Default"), _profile("profile-2", "Default")])

    with pytest.raises(argparse.ArgumentError, match="ambiguous"):
        _run_command(monkeypatch, site_client, {"profile": "Default"})


def test_port_profiles_command_rejects_unknown_profile(monkeypatch):
    site_client = FakeSiteClient([_profile("profile-1", "Default")])

    with pytest.raises(argparse.ArgumentError, match="not found"):
        _run_command(monkeypatch, site_client, {"profile": "Missing"})
