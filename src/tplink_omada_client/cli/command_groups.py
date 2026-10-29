"""Ordinary CLI management of IP, IP-port and MAC groups."""

import asyncio
import json
import re
from argparse import ArgumentParser
from dataclasses import replace
from typing import Any, Literal, overload

from tplink_omada_client.exceptions import GroupWriteUncertain, LoginFailed, OmadaClientException, RequestFailed
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
    _safe_controller_endpoint,
)
from tplink_omada_client.groups import (
    build_group_delete,
    build_group_update,
    group_payload,
    parse_port,
    resolve_group_target,
)
from tplink_omada_client.networks import GroupProfile

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_target_argument

_KINDS = {"ip": GroupType.IP, "ip-port": GroupType.IP_PORT, "mac": GroupType.MAC}
_LABELS: dict[int, str] = {value: key for key, value in _KINDS.items()}


def _subnet(value: str) -> IpSubnet:
    parts = value.split("/")
    if len(parts) != 2:
        raise ValueError("Expected ADDRESS/PREFIX")
    return IpSubnet(parts[0], int(parts[1]))


def _mac(value: str) -> MacMember:
    if "=" in value:
        name, address = value.rsplit("=", 1)
        return MacMember(address, name)
    return MacMember(value)


@overload
def _request(args: dict[str, Any], kind: GroupType | None, *, create: Literal[True]) -> GroupCreate: ...


@overload
def _request(args: dict[str, Any], kind: GroupType | None, *, create: Literal[False]) -> GroupUpdate: ...


def _request(args: dict[str, Any], kind: GroupType | None, *, create: bool) -> GroupCreate | GroupUpdate:
    if kind is None:
        raise ValueError("Select a group kind")
    subnets, ports, members = args.get("subnet"), args.get("port"), args.get("mac")
    clear = args.get("clear_subnets", False)
    if (members is not None and kind != GroupType.MAC) or (kind == GroupType.MAC and subnets is not None):
        raise ValueError("Membership options do not match the group kind")
    if (ports is not None or clear) and kind != GroupType.IP_PORT:
        raise ValueError("Ports and --clear-subnets require an IP-port group")
    name = args.get("name")
    if create:
        if name is None:
            raise ValueError("Group name is required")
        if kind == GroupType.IP:
            return IpGroupCreate(name, tuple(subnets or ()))
        if kind == GroupType.IP_PORT:
            return IpPortGroupCreate(name, () if clear or subnets is None else tuple(subnets), tuple(ports or ()))
        return MacGroupCreate(name, tuple(members or ()))
    if kind == GroupType.IP:
        return IpGroupUpdate(name, subnets)
    if kind == GroupType.IP_PORT:
        return IpPortGroupUpdate(name, () if clear else subnets, ports)
    return MacGroupUpdate(name, members)


@overload
def _safe_data(value: dict[str, Any]) -> dict[str, Any]: ...


@overload
def _safe_data(value: object) -> object: ...


def _safe_data(value: object) -> object:
    if isinstance(value, dict):
        return {key: ("[redacted]" if any(part in key.lower() for part in
                     ("password", "token", "secret", "private", "cookie", "csrf", "session", "credential")) else _safe_data(item))
                for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_data(item) for item in value]
    return value


def _member_summary(profile: GroupProfile) -> str:
    raw = profile.raw_data
    ips, ports, macs = (raw.get(key) for key in ("ipList", "portList", "macAddressList"))
    if type(profile.group_type) is not int:
        return "Membership unavailable"
    if profile.group_type == GroupType.MAC:
        return f"{len(macs)} MAC member(s)" if isinstance(macs, list) else "MAC membership unavailable"
    ip_summary = f"{len(ips)} subnet(s)" if isinstance(ips, list) else "IP membership unavailable"
    if profile.group_type == GroupType.IP_PORT:
        scope = "any IP (no IP restriction)" if ips in (None, []) else ip_summary
        port_summary = f"{len(ports)} port(s)" if isinstance(ports, list) else "Port membership unavailable"
        return f"{scope}; {port_summary}"
    return ip_summary if profile.group_type == GroupType.IP else "Unsupported membership"


def _print_group(args, profile: GroupProfile, *, detail: bool = False) -> None:
    try:
        group_payload(profile)
        state = "writable"
    except (ValueError, TypeError, KeyError) as error:
        state = str(error)
    safe = _safe_data(profile.raw_data)
    label = (_LABELS.get(profile.group_type, f"unsupported({profile.group_type})")
             if type(profile.group_type) is int else "malformed kind")
    print(f"{label:15} {safe.get('groupId')!s:32} {safe.get('name')} [{state}]")
    print(f"    Members: {_member_summary(profile)}")
    if detail:
        for key in ("count", "ipList", "portList", "macAddressList"):
            print(f"    {key}: {json.dumps(safe.get(key), ensure_ascii=False)}")
    dump_raw_data(args, GroupProfile(safe))


def _print_preview(preview) -> None:
    target = f" {preview.identity.id}" if preview.identity else ""
    print(f"Preview {preview.operation}{target}" + (" (no-op)" if preview.no_op else ""))
    if preview.before is not None and preview.after is not None:
        keys = (preview.before.keys() & preview.after.keys()) - {"id", "groupId"}
        changed = sorted(key for key in keys if preview.before[key] != preview.after[key])
        preserved = sorted(keys - set(changed))
        print(f"Changed fields: {', '.join(changed) or '(none)'}")
        print(f"Preserved fields: {', '.join(preserved) or '(none)'}")
    for label, value in (("Before", preview.before), ("After", preview.after)):
        if value is not None:
            print(f"{label}: {json.dumps(_safe_data(value), indent=2, ensure_ascii=False)}")
    for warning in preview.warnings:
        print(f"Warning: {warning}")


def _identity(args, profiles):
    kind = _KINDS.get(args.get("type"))
    if args.get("id") is not None and kind is None:
        raise ValueError("--id requires --type")
    target = args.get("id") if args.get("id") is not None else args.get("group")
    if not target:
        raise ValueError("Select a group by name or ID")
    return resolve_group_target(target, profiles, kind, by_id=args.get("id") is not None)


def _inspect(args, profiles) -> int:
    kind = _KINDS.get(args.get("type"))
    if args["group_operation"] == "list":
        for profile in profiles:
            if kind is None or profile.group_type == kind:
                _print_group(args, profile)
    else:
        identity = _identity(args, profiles)
        profile = next(p for p in profiles if (p.group_type, p.id) == (identity.group_type, identity.id))
        _print_group(args, profile, detail=True)
    return 0


async def _apply(site_client, operation, request, preview) -> None:
    if operation == "create":
        result = await site_client.create_group(request)
        print(f"Verified group create: {result.id} {result.name}")
    elif operation == "modify":
        result = await site_client.update_group(preview.identity, request, expected_data=preview.before)
        print(f"Verified group update: {result.id} {result.name}" + (" (no-op)" if preview.no_op else ""))
    elif operation == "delete":
        await site_client.delete_group(preview.identity, expected_data=preview.before)
        print(f"Verified group delete: {preview.identity.id}")
    else:
        raise ValueError("Unsupported group operation")


async def _execute(args, config) -> int:
    operation = args.get("group_operation")
    if operation not in {"list", "show", "create", "modify", "delete"}:
        raise ValueError("Unsupported group operation")
    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        context = site_client.group_context
        print(f"Target: {args.get('target') or '(configured default)'}; "
              f"controller: {context.controller} ({context.controller_id}); site: {config.site} ({context.site_id})")
        if operation == "create":
            request = _request(args, _KINDS.get(args.get("type")), create=True)
            preview = await site_client.preview_group_create(request)
        else:
            profiles = await site_client.get_groups()
            if operation in ("list", "show"):
                return _inspect(args, profiles)
            identity = _identity(args, profiles)
            if operation == "modify":
                request = _request(args, identity.group_type, create=False)
                preview = build_group_update(identity, request, profiles)
            else:
                request = None
                preview = build_group_delete(identity, profiles)
        preview = replace(preview, context=context)
        _print_preview(preview)
        if not args.get("apply"):
            print("Preview only; use --apply to change group settings.")
            return 0
        await _apply(site_client, operation, request, preview)
    return 0


def _error_message(error, config) -> str:
    """Never render raw malformed responses or secret-bearing server messages."""
    secret_parts = ("password", "token", "secret", "private", "cookie", "csrf", "session", "credential")
    if isinstance(error, RequestFailed):
        valid_code = type(error._error_code) is int
        if (not valid_code or not error.application_rejection or not isinstance(error._msg, str)
                or any(part in error._msg.lower() for part in secret_parts)):
            code = error._error_code if valid_code else "unknown"
            message = f"Omada controller request failed ({code}); response details omitted"
        else:
            message = str(error)
    elif not isinstance(error, GroupWriteUncertain) and any(part in str(error).lower() for part in secret_parts):
        message = f"{type(error).__name__}: sensitive response details omitted"
    else:
        message = str(error) or type(error).__name__
    message = re.sub(r"https?://[^\s'\"<>]+", lambda match: _safe_controller_endpoint(match[0]), message, flags=re.IGNORECASE)
    if config is not None:
        for value in (config.password, config.username):
            if value:
                message = message.replace(value, "[redacted]")
    return message


async def command_groups(args) -> int:
    """Run a group operation with existing CLI configuration/error conventions."""
    config = None
    try:
        config = get_target_config(get_target_argument(args))
        return await _execute(args, config)
    except asyncio.CancelledError as error:
        recovery = getattr(error, "group_recovery", None)
        if isinstance(recovery, GroupWriteUncertain):
            print(_error_message(recovery, config))
        raise
    except LoginFailed as error:
        print(f"Login failed: {_error_message(error, config)}")
        return 2
    except (OmadaClientException, TimeoutError, ValueError, TypeError, KeyError) as error:
        print(f"Group command failed: {_error_message(error, config)}")
        return 1


def _selection(parser) -> None:
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("group", nargs="?", help="Group ID or exact name")
    selection.add_argument("--id", help="Exact group ID (requires --type)")


def _members(parser, *, create: bool) -> None:
    parser.add_argument("--name", required=create, help="Group name")
    subnets = parser.add_mutually_exclusive_group()
    subnets.add_argument("--subnet", action="append", type=_subnet, help="IPv4 ADDRESS/PREFIX; repeats replace membership")
    if not create:
        subnets.add_argument("--clear-subnets", action="store_true", help="IP-port only: remove the IP restriction")
    parser.add_argument("--port", action="append", type=parse_port, help="PORT or LOW-HIGH; repeats replace ports")
    parser.add_argument("--mac", action="append", type=_mac, help="ADDRESS or NAME=ADDRESS; repeats replace MAC members")


def arg_parser(subparsers) -> None:
    """Register normal group subcommands without changing global CLI behaviour."""
    parser: ArgumentParser = subparsers.add_parser("group", help="Inspect and manage IP, IP-port and MAC groups")
    parser.set_defaults(func=command_groups)
    operations = parser.add_subparsers(dest="group_operation", required=True)
    for operation in ("list", "show", "create", "modify", "delete"):
        command = operations.add_parser(operation)
        command.add_argument("--type", choices=_KINDS, required=operation == "create", help="Group kind")
        command.set_defaults(dump=False)
        if operation in ("show", "modify", "delete"):
            _selection(command)
        if operation in ("list", "show"):
            command.add_argument("-d", "--dump", action="store_true", help="Dump diagnostic group data")
        else:
            command.add_argument("--apply", action="store_true", help="Apply and verify (default: preview only)")
        if operation in ("create", "modify"):
            _members(command, create=operation == "create")
