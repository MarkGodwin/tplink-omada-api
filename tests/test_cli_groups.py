"""Ordinary CLI group workflows using the real lifecycle and offline transport."""

import importlib
from copy import deepcopy

import pytest
from test_group_management import GROUPS, ack, inventory, site

from tplink_omada_client import cli
from tplink_omada_client.cli.config import ControllerConfig


class Connection:
    def __init__(self, client):
        self.client = client

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get_site_client(self, name):
        assert name == "Default"
        return self.client


def run(monkeypatch, responses, argv):
    module = importlib.import_module("tplink_omada_client.cli.command_groups")
    client, session = site(responses)
    config = ControllerConfig("https://omada.example", "operator", "do-not-print", "Default", True)
    monkeypatch.setattr(module, "get_target_config", lambda _: config)
    monkeypatch.setattr(module, "to_omada_connection", lambda _: Connection(client))
    result = cli.main(["-t", "example", "group", *argv])
    return result, session


def test_list_shows_all_kinds_and_ids(monkeypatch, capsys):
    result, session = run(monkeypatch, [inventory(GROUPS)], ["list"])
    assert result == 0
    output = capsys.readouterr().out
    assert all(row["groupId"] in output for row in GROUPS)
    assert "do-not-print" not in output
    assert len(session.calls) == 1


def test_show_by_name_and_dump(monkeypatch, capsys):
    result, _ = run(monkeypatch, [inventory(GROUPS)], ["show", "Example devices", "--dump"])
    assert result == 0
    output = capsys.readouterr().out
    assert "example-rule" in output
    assert "02-AA-BB-CC-DD-01" in output


@pytest.mark.parametrize("kind,options", [("ip", ["--subnet", "192.0.2.8/32"]),
                                         ("ip-port", ["--port", "443"]),
                                         ("mac", ["--mac", "phone=02:aa:bb:cc:dd:02"])])
def test_create_defaults_to_preview_for_all_kinds(monkeypatch, capsys, kind, options):
    result, session = run(monkeypatch, [inventory(GROUPS)], ["create", "--type", kind, "--name", "New", *options])
    assert result == 0
    output = capsys.readouterr().out
    assert "Preview" in output and "Verified" not in output
    assert all(call[0] == "get" for call in session.calls)
    if kind == "ip-port":
        assert "any IP" in output


@pytest.mark.parametrize("operation", ["modify", "delete"])
def test_apply_by_normal_positional_selection_needs_no_token(monkeypatch, capsys, operation):
    changed = {**GROUPS[0], "name": "Renamed"}
    argv = [operation, "Example hosts", "--apply"]
    if operation == "modify":
        argv += ["--name", "Renamed"]
    rows = [changed] if operation == "modify" else []
    result, session = run(monkeypatch, [inventory(GROUPS), inventory(GROUPS), ack(), inventory(rows)], argv)
    assert result == 0
    assert "Verified" in capsys.readouterr().out
    assert [call[0] for call in session.calls] == ["get", "get", "patch" if operation == "modify" else "delete", "get"]


def test_explicit_id_selection_and_noop(monkeypatch, capsys):
    result, session = run(monkeypatch, [inventory(GROUPS), inventory(GROUPS)],
                          ["modify", "--type", "ip", "--id", "ip-example", "--name", "Example hosts", "--apply"])
    assert result == 0
    assert "no-op" in capsys.readouterr().out.lower()
    assert all(call[0] == "get" for call in session.calls)


def test_stale_same_invocation_target_is_rejected(monkeypatch, capsys):
    changed = deepcopy(GROUPS)
    changed[0]["count"] = 7
    result, session = run(monkeypatch, [inventory(GROUPS), inventory(changed)],
                          ["modify", "ip-example", "--name", "Renamed", "--apply"])
    assert result != 0
    output = capsys.readouterr().out
    assert "changed" in output and "Verified" not in output
    assert all(call[0] == "get" for call in session.calls)


@pytest.mark.parametrize("argv", [["modify", "ip-example", "--mac", "02:aa:bb:cc:dd:02", "--apply"],
                                 ["delete", "missing", "--apply"],
                                 ["modify", "ip-example", "--clear-subnets", "--apply"]])
def test_invalid_selection_or_wrong_kind_never_mutates(monkeypatch, capsys, argv):
    result, session = run(monkeypatch, [inventory(GROUPS)], argv)
    assert result != 0
    assert "Verified" not in capsys.readouterr().out
    assert all(call[0] == "get" for call in session.calls)


@pytest.mark.parametrize("operation", ["create", "modify", "delete"])
def test_uncertain_cli_write_has_guidance_and_no_false_success(monkeypatch, capsys, operation):
    argv = [operation]
    if operation == "create":
        argv += ["--type", "ip", "--name", "New", "--subnet", "192.0.2.8/32"]
    else:
        argv += ["ip-example"]
        if operation == "modify":
            argv += ["--name", "New"]
    result, session = run(monkeypatch, [inventory(GROUPS), inventory(GROUPS), ack(), TimeoutError("lost read-back")], [*argv, "--apply"])
    assert result != 0
    output = capsys.readouterr().out
    assert "may have succeeded" in output and "inspect" in output
    assert "Verified" not in output
    assert sum(call[0] in ("post", "patch", "delete") for call in session.calls) == 1


def test_unknown_kind_list_and_diagnostic_dump_remain_inspectable(monkeypatch, capsys):
    result, _ = run(monkeypatch, [inventory([{**GROUPS[0], "type": 9}])], ["list", "--dump"])
    assert result == 0
    output = capsys.readouterr().out
    assert "unsupported" in output.lower() and "ip-example" in output


def test_mac_alias_split_at_last_equals_and_explicit_clearing(monkeypatch, capsys):
    result, _ = run(monkeypatch, [inventory(GROUPS)],
                    ["modify", "mac-example", "--mac", "room=phone=02:aa:bb:cc:dd:01"])
    assert result == 0
    assert "room=phone" in capsys.readouterr().out
    result, _ = run(monkeypatch, [inventory(GROUPS)], ["modify", "mac-example", "--mac", "=02:aa:bb:cc:dd:01"])
    assert result == 0
    assert '"name": ""' in capsys.readouterr().out


def test_cancelled_cli_write_prints_recovery_without_false_success(monkeypatch, capsys):
    import asyncio

    with pytest.raises(asyncio.CancelledError):
        run(monkeypatch, [inventory(GROUPS), inventory(GROUPS), asyncio.CancelledError()],
            ["delete", "ip-example", "--apply"])
    output = capsys.readouterr().out
    assert "may have succeeded" in output and "inspect" in output
    assert "Verified" not in output


def test_dump_redacts_unknown_secret_metadata(monkeypatch, capsys):
    row = {**GROUPS[0], "csrfToken": "hidden-session-material"}
    result, _ = run(monkeypatch, [inventory([row])], ["list", "--dump"])
    assert result == 0
    output = capsys.readouterr().out
    assert "hidden-session-material" not in output and "[redacted]" in output


def test_create_apply_uses_existing_conventions(monkeypatch, capsys):
    row = {**GROUPS[0], "groupId": "new-id", "name": "New"}
    result, session = run(monkeypatch, [inventory(GROUPS), inventory(GROUPS), ack(), inventory([*GROUPS, row])],
                          ["create", "--type", "ip", "--name", "New", "--subnet", "192.0.2.7/32", "--apply"])
    assert result == 0
    assert "Verified group create: new-id" in capsys.readouterr().out
    assert sum(call[0] == "post" for call in session.calls) == 1
