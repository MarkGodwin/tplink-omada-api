"""Typed CLI requests retain membership and redaction behavior."""

import asyncio
import importlib
from typing import Any, assert_type

import pytest
from test_cli_groups import Connection
from test_cli_groups import run as cli_run
from test_group_management import GROUPS, ack, inventory, site

from tplink_omada_client.cli.command_groups import _request, _safe_data
from tplink_omada_client.cli.config import ControllerConfig
from tplink_omada_client.group_models import (
    GroupCreate,
    GroupType,
    GroupUpdate,
    IpGroupCreate,
    IpGroupUpdate,
    IpPortGroupCreate,
    IpPortGroupUpdate,
    IpSubnet,
    MacGroupCreate,
    MacGroupUpdate,
    MacMember,
    PortRange,
)
from tplink_omada_client.groups import build_group_create


@pytest.mark.parametrize("kind,arguments,expected", [
    (GroupType.IP, {"name": "IP", "subnet": [IpSubnet("192.0.2.7", 32)]},
     IpGroupCreate("IP", (IpSubnet("192.0.2.7", 32),))),
    (GroupType.IP_PORT, {"name": "Ports", "port": [PortRange(443, 443)]},
     IpPortGroupCreate("Ports", (), (PortRange(443, 443),))),
    (GroupType.MAC, {"name": "MAC", "mac": [MacMember("02-AA-BB-CC-DD-01", "Phone")]},
     MacGroupCreate("MAC", (MacMember("02-AA-BB-CC-DD-01", "Phone"),))),
])
def test_create_request_type_and_membership(kind, arguments, expected):
    request = assert_type(_request(arguments, kind, create=True), GroupCreate)
    assert request == expected


@pytest.mark.parametrize("kind,arguments,expected", [
    (GroupType.IP, {}, IpGroupUpdate()),
    (GroupType.IP_PORT, {"clear_subnets": True}, IpPortGroupUpdate(subnets=())),
    (GroupType.MAC, {"mac": [MacMember("02-AA-BB-CC-DD-01")]},
     MacGroupUpdate(members=(MacMember("02-AA-BB-CC-DD-01"),))),
])
def test_update_request_type_preserves_omitted_fields(kind, arguments, expected):
    request = assert_type(_request(arguments, kind, create=False), GroupUpdate)
    assert request == expected


@pytest.mark.parametrize("kind,expected", [
    (GroupType.IP, IpGroupCreate("Empty", ())),
    (GroupType.IP_PORT, IpPortGroupCreate("Empty", (), ())),
    (GroupType.MAC, MacGroupCreate("Empty", ())),
])
def test_missing_create_membership_stays_typed_and_is_rejected(kind, expected):
    request = assert_type(_request({"name": "Empty"}, kind, create=True), GroupCreate)
    assert request == expected
    with pytest.raises(ValueError):
        build_group_create(request, [])


def test_redaction_preserves_dictionary_shape_and_input():
    source = {"token": "sensitive-session", "members": [{"password": "do-not-print", "name": "Phone"}]}
    safe = assert_type(_safe_data(source), dict[str, Any])
    assert safe == {"token": "[redacted]", "members": [{"password": "[redacted]", "name": "Phone"}]}
    assert source == {"token": "sensitive-session", "members": [{"password": "do-not-print", "name": "Phone"}]}


@pytest.mark.parametrize("kind,arguments,message", [
    (None, {"name": "Empty"}, "Select a group kind"),
    (GroupType.IP, {}, "Group name is required"),
])
def test_missing_create_selection_or_name_is_rejected(kind, arguments, message):
    with pytest.raises(ValueError, match=message):
        _request(arguments, kind, create=True)


@pytest.mark.parametrize("kind", ["ip", "ip-port", "mac"])
def test_missing_create_membership_cannot_dispatch(monkeypatch, capsys, kind):
    result, session = cli_run(monkeypatch, [], ["create", "--type", kind, "--name", "Empty", "--apply"])
    assert result == 1 and "Group command failed" in capsys.readouterr().out
    assert session.calls == []


def _programmatic_create_setup(monkeypatch, expected_ips):
    module = importlib.import_module("tplink_omada_client.cli.command_groups")
    row = {"groupId": "typed-create-id", "name": "Typed boundary", "type": 1, "count": None,
           "ipList": expected_ips, "portList": ["443"], "macAddressList": None}
    client, session = site([inventory(GROUPS), inventory(GROUPS), ack(), inventory([*GROUPS, row])])
    monkeypatch.setattr(module, "to_omada_connection", lambda _: Connection(client))
    config = ControllerConfig("https://omada.example", "operator", "do-not-print", "Default", True)
    return module, config, session


@pytest.mark.parametrize("kind,field,members", [
    ("ip", "subnet", {"subnet": [IpSubnet("192.0.2.7", 32)]}),
    ("ip-port", "subnet", {"port": [PortRange(443, 443)]}),
    ("ip-port", "port", {"port": [PortRange(443, 443)]}),
    ("mac", "mac", {"mac": [MacMember("02-AA-BB-CC-DD-01")]}),
])
@pytest.mark.parametrize("invalid", [False, 0], ids=["false", "zero"])
def test_malformed_programmatic_membership_cannot_dispatch(monkeypatch, kind, field, members, invalid):
    module, config, session = _programmatic_create_setup(monkeypatch, [])
    args = {"group_operation": "create", "type": kind, "name": "Typed boundary", "apply": True,
            **members, field: invalid}
    with pytest.raises((TypeError, ValueError)):
        asyncio.run(module._execute(args, config))
    assert session.calls == []


@pytest.mark.parametrize("fields,expected_ips", [
    ({}, []),
    ({"subnet": None}, []),
    ({"subnet": []}, []),
    ({"subnet": [IpSubnet("192.0.2.7", 32)]}, [{"ip": "192.0.2.7", "mask": "32"}]),
], ids=["omitted", "none", "empty", "restricted"])
def test_programmatic_subnet_defaults_preserve_requested_scope(monkeypatch, fields, expected_ips):
    module, config, session = _programmatic_create_setup(monkeypatch, expected_ips)
    args = {"group_operation": "create", "type": "ip-port", "name": "Typed boundary", "apply": True,
            "port": [PortRange(443, 443)], **fields}
    assert asyncio.run(module._execute(args, config)) == 0
    assert [call[0] for call in session.calls] == ["get", "get", "post", "get"]
    assert session.calls[2][1].endswith("/setting/profiles/groups")
    assert session.calls[2][2] == {"id": None, "name": "Typed boundary", "type": 1, "count": None,
                                   "ipList": expected_ips, "portList": ["443"], "macAddressList": None}
