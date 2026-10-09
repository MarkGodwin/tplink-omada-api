"""Tests for the 'sync-names' CLI command."""

import asyncio
from types import SimpleNamespace

import dns.exception
import dns.resolver
import pytest

from tplink_omada_client.cli import command_sync_names
from tplink_omada_client.cli.config import ControllerConfig
from tplink_omada_client.clients import OmadaWiredClient


def _client(mac: str, name: str, ip: str | None) -> OmadaWiredClient:
    data = {"mac": mac, "name": name, "guest": False}
    if ip is not None:
        data["ip"] = ip
    return OmadaWiredClient(data)


def _answer(fqdn: str):
    return [SimpleNamespace(target=fqdn)]


class FakeSiteClient:
    def __init__(self, clients: list[OmadaWiredClient]) -> None:
        self.clients = clients
        self.update_calls: list[tuple[str, str | None]] = []

    async def get_connected_clients(self):
        for connected_client in self.clients:
            yield connected_client

    async def update_client(self, mac, settings):
        self.update_calls.append((mac, settings.name))


class FakeConnection:
    def __init__(self, site_client: FakeSiteClient) -> None:
        self.site_client = site_client

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get_site_client(self, site: str) -> FakeSiteClient:
        return self.site_client


def _run_command(monkeypatch, site_client: FakeSiteClient, dry_run: bool = False, dns_server: str | None = None) -> int:
    config = ControllerConfig("url", "user", "pass", "Default", True)
    monkeypatch.setattr(command_sync_names, "get_target_config", lambda target: config)
    monkeypatch.setattr(command_sync_names, "to_omada_connection", lambda target_config: FakeConnection(site_client))
    return asyncio.run(
        command_sync_names.command_sync_names({"target": "", "dry_run": dry_run, "dns_server": dns_server})
    )


def test_resolve_hostname_returns_short_name(monkeypatch):
    monkeypatch.setattr(dns.resolver.Resolver, "resolve_address", lambda self, ip: _answer("desktop.lan.example.com."))

    hostname = asyncio.run(
        command_sync_names._resolve_hostname(_client("mac-1", "old-name", "192.0.2.5"), dns.resolver.Resolver())
    )

    assert hostname == "desktop"


def test_resolve_hostname_returns_none_when_lookup_fails(monkeypatch):
    def _raise(self, ip):
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve_address", _raise)

    hostname = asyncio.run(
        command_sync_names._resolve_hostname(_client("mac-1", "old-name", "192.0.2.5"), dns.resolver.Resolver())
    )

    assert hostname is None


def test_resolve_hostname_returns_none_when_client_has_no_ip():
    hostname = asyncio.run(
        command_sync_names._resolve_hostname(_client("mac-1", "old-name", None), dns.resolver.Resolver())
    )

    assert hostname is None


def test_resolve_hostname_uses_configured_dns_server(monkeypatch):
    seen_nameservers = []

    def _fake_resolve_address(self, ip):
        seen_nameservers.append(self.nameservers)
        return _answer("desktop.lan.")

    monkeypatch.setattr(dns.resolver.Resolver, "resolve_address", _fake_resolve_address)

    resolver = dns.resolver.Resolver()
    resolver.nameservers = ["10.0.5.5"]
    asyncio.run(command_sync_names._resolve_hostname(_client("mac-1", "old-name", "192.0.2.5"), resolver))

    assert seen_nameservers == [["10.0.5.5"]]


def test_resolve_hostname_returns_none_for_empty_answer(monkeypatch):
    monkeypatch.setattr(dns.resolver.Resolver, "resolve_address", lambda self, ip: [])

    hostname = asyncio.run(
        command_sync_names._resolve_hostname(_client("mac-1", "old-name", "192.0.2.5"), dns.resolver.Resolver())
    )

    assert hostname is None


def test_resolve_hostname_returns_none_for_blank_resolved_name(monkeypatch):
    monkeypatch.setattr(dns.resolver.Resolver, "resolve_address", lambda self, ip: _answer("."))

    hostname = asyncio.run(
        command_sync_names._resolve_hostname(_client("mac-1", "old-name", "192.0.2.5"), dns.resolver.Resolver())
    )

    assert hostname is None


def test_command_updates_clients_with_resolvable_names(monkeypatch, capsys):
    monkeypatch.setattr(dns.resolver.Resolver, "resolve_address", lambda self, ip: _answer("desktop.lan."))
    site_client = FakeSiteClient([_client("mac-1", "old-name", "192.0.2.5")])

    assert _run_command(monkeypatch, site_client) == 0

    assert site_client.update_calls == [("mac-1", "desktop")]
    assert "old-name -> desktop" in capsys.readouterr().out


def test_command_dry_run_reports_without_updating(monkeypatch, capsys):
    monkeypatch.setattr(dns.resolver.Resolver, "resolve_address", lambda self, ip: _answer("desktop.lan."))
    site_client = FakeSiteClient([_client("mac-1", "old-name", "192.0.2.5")])

    assert _run_command(monkeypatch, site_client, dry_run=True) == 0

    assert site_client.update_calls == []
    assert "[dry run] mac-1 192.0.2.5: old-name -> desktop" in capsys.readouterr().out


def test_command_skips_clients_already_matching_resolved_name(monkeypatch):
    monkeypatch.setattr(dns.resolver.Resolver, "resolve_address", lambda self, ip: _answer("desktop.lan."))
    site_client = FakeSiteClient([_client("mac-1", "desktop", "192.0.2.5")])

    assert _run_command(monkeypatch, site_client) == 0

    assert site_client.update_calls == []


def test_command_skips_clients_with_unresolvable_ip(monkeypatch):
    def _raise(self, ip):
        raise dns.exception.Timeout()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve_address", _raise)
    site_client = FakeSiteClient([_client("mac-1", "old-name", "192.0.2.5")])

    assert _run_command(monkeypatch, site_client) == 0

    assert site_client.update_calls == []


def test_command_passes_dns_server_to_resolver(monkeypatch):
    seen_nameservers = []

    def _fake_resolve_address(self, ip):
        seen_nameservers.append(self.nameservers)
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve_address", _fake_resolve_address)
    site_client = FakeSiteClient([_client("mac-1", "old-name", "192.0.2.5")])

    assert _run_command(monkeypatch, site_client, dns_server="10.0.5.5") == 0

    assert seen_nameservers == [["10.0.5.5"]]


def test_main_registers_sync_names_command(monkeypatch):
    from tplink_omada_client import cli

    seen = {}

    async def fake_command(args):
        seen.update(args)
        return 0

    monkeypatch.setattr(cli.command_sync_names, "command_sync_names", fake_command)

    assert cli.main(["sync-names"]) == 0
    assert seen["target"] == ""
    assert seen["dry_run"] is False
    assert seen["dns_server"] is None


def test_main_parses_dry_run_flag(monkeypatch):
    from tplink_omada_client import cli

    seen = {}

    async def fake_command(args):
        seen.update(args)
        return 0

    monkeypatch.setattr(cli.command_sync_names, "command_sync_names", fake_command)

    assert cli.main(["sync-names", "--dry-run"]) == 0
    assert seen["dry_run"] is True


def test_main_parses_dns_server_flag(monkeypatch):
    from tplink_omada_client import cli

    seen = {}

    async def fake_command(args):
        seen.update(args)
        return 0

    monkeypatch.setattr(cli.command_sync_names, "command_sync_names", fake_command)

    assert cli.main(["sync-names", "--dns-server", "10.0.5.5"]) == 0
    assert seen["dns_server"] == "10.0.5.5"


def test_main_rejects_invalid_dns_server(capsys):
    from tplink_omada_client import cli

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["sync-names", "--dns-server", "not-an-ip"])

    assert exc_info.value.code == 2
    assert "not a valid IP address" in capsys.readouterr().err
