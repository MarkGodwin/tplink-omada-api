"""Pure validation, preservation and payload construction for group settings."""

import json
import re
import unicodedata
from collections.abc import Sequence
from copy import deepcopy
from ipaddress import IPv4Address
from typing import Any

from .group_models import (
    GroupCreate,
    GroupIdentity,
    GroupPreview,
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
    _port,
    parse_port,
)
from .networks import GroupProfile

_CREATE_TYPES = {IpGroupCreate: GroupType.IP, IpPortGroupCreate: GroupType.IP_PORT, MacGroupCreate: GroupType.MAC}
_UPDATE_TYPES = {IpGroupUpdate: GroupType.IP, IpPortGroupUpdate: GroupType.IP_PORT, MacGroupUpdate: GroupType.MAC}
_FIELDS = {"groupId", "name", "type", "count", "ipList", "portList", "macAddressList",
           "site", "resource", "portType", "portMaskList"}


def _text(value: Any, *, blank=False) -> str:
    if not isinstance(value, str) or any(unicodedata.category(c) in ("Cc", "Cs") for c in value):
        raise ValueError("Expected text without control characters or invalid Unicode")
    if not blank and not value.strip():
        raise ValueError("Text must not be blank")
    return value


def _name(value: Any) -> str:
    value = _text(value).strip()
    if len(value.encode("utf-16-le")) // 2 > 64:
        raise ValueError("Group name exceeds 64 UTF-16 code units")
    return value


def _safe_id(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Missing or unsafe group ID")
    return value


def validate_inventory(inventory: Sequence[GroupProfile]) -> None:
    seen = set()
    for profile in inventory:
        raw = profile.raw_data
        identifier = _safe_id(raw.get("groupId"))
        kind = raw.get("type")
        if type(kind) is not int or kind < 0:
            raise ValueError("Missing or malformed group kind")
        _name(raw.get("name"))
        key = (kind, identifier)
        if key in seen:
            raise ValueError("Duplicate group identity in inventory")
        seen.add(key)


def resolve_group_target(target: str, inventory: Sequence[GroupProfile], group_type: GroupType | None = None,
                         *, by_id: bool = False) -> GroupIdentity:
    validate_inventory(inventory)
    selected = [p for p in inventory if group_type is None or p.group_type == group_type]
    matches = [p for p in selected if p.id == target]
    if not matches and not by_id:
        matches = [p for p in selected if p.name == target]
    if len(matches) != 1:
        raise ValueError("Group target is missing or ambiguous; select its kind and ID")
    try:
        kind = GroupType(matches[0].group_type)
    except ValueError as error:
        raise ValueError("Unsupported group kind") from error
    return GroupIdentity(kind, _safe_id(matches[0].id))


def selected_group(identity: GroupIdentity, inventory: Sequence[GroupProfile]) -> GroupProfile:
    validate_inventory(inventory)
    if not isinstance(identity, GroupIdentity) or not isinstance(identity.group_type, GroupType):
        raise TypeError("Expected a typed group identity")
    _safe_id(identity.id)
    matches = [p for p in inventory if p.group_type == identity.group_type and p.id == identity.id]
    if len(matches) != 1:
        raise ValueError("Bound group identity is missing or ambiguous")
    return matches[0]


def _known_fields(raw: dict, allowed: set[str]) -> None:
    if not isinstance(raw, dict) or any(value is not None for key, value in raw.items() if key not in allowed):
        raise ValueError("Unsupported non-null group configuration")


def _response_metadata(raw: dict) -> None:
    if raw.get("site") is not None:
        _safe_id(raw["site"])
    resource = raw.get("resource")
    if resource is not None and (type(resource) is not int or resource != 0):
        raise ValueError("Unsupported group resource marker")
    port_type = raw.get("portType")
    if port_type is not None and (type(port_type) is not int or port_type != 0):
        raise ValueError("Unsupported group port mode")
    if raw.get("portMaskList") not in (None, []):
        raise ValueError("Unsupported group port masks")


def _unique(values: list) -> list:
    keys = [json.dumps(v, sort_keys=True) for v in values]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate group members")
    return values


def _ip(item: IpSubnet) -> dict:
    if not isinstance(item, IpSubnet) or type(item.prefix) is not int or not 0 <= item.prefix <= 32:
        raise ValueError("Expected an IPv4 address and prefix 0..32")
    try:
        address = str(IPv4Address(item.ip)) if isinstance(item.ip, str) else None
    except ValueError as error:
        raise ValueError("Invalid IPv4 address") from error
    if address is None:
        raise ValueError("Expected an IPv4 address")
    return {"ip": address, "mask": str(item.prefix)}


def _ips(values, kind: GroupType, *, replacement=True) -> list[dict]:
    result = _unique([_ip(item) for item in values])
    minimum = 1 if kind == GroupType.IP else 0
    maximum = 16 if kind == GroupType.IP else 8
    if len(result) < minimum or (replacement and len(result) > maximum):
        raise ValueError(f"Supported IP membership count is {minimum}..{maximum}")
    return result


def _ports(values) -> list[str]:
    result = _unique([_port(item) for item in values])
    if not result:
        raise ValueError("IP-port groups need at least one port")
    return result


def canonical_mac(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Expected a MAC address")
    value = value.strip().replace(":", "-").upper()
    if not re.fullmatch(r"[0-9A-F]{2}(?:-[0-9A-F]{2}){5}", value):
        raise ValueError("Expected a complete 48-bit MAC address")
    return value


def _macs(values, current=()) -> list[dict]:
    retained = {canonical_mac(row["macAddress"]): row for row in current}
    result = []
    seen = set()
    for item in values:
        if not isinstance(item, MacMember):
            raise TypeError("Expected a typed MAC member")
        address = canonical_mac(item.address)
        if address in seen:
            raise ValueError("Duplicate MAC address")
        seen.add(address)
        row = deepcopy(retained.get(address, {"name": None}))
        row["macAddress"] = address
        if item.name is not None:
            row["name"] = _text(item.name, blank=True)
        result.append(row)
    if not result:
        raise ValueError("MAC groups need at least one member")
    return result


def _current_ips(rows, kind: GroupType) -> list[dict]:
    if not isinstance(rows, list):
        raise TypeError("Malformed IP membership")
    members = []
    for row in rows:
        _known_fields(row, {"ip", "mask"})
        mask = row.get("mask")
        if type(mask) is int:
            prefix = mask
        elif isinstance(mask, str) and re.fullmatch(r"[0-9]{1,2}", mask):
            prefix = int(mask)
        else:
            raise ValueError("Malformed IP prefix")
        members.append(IpSubnet(row.get("ip"), prefix))
    return _ips(members, kind, replacement=False)


def _current_ip_payload(rows, kind: GroupType) -> list[dict]:
    _current_ips(rows, kind)
    result = deepcopy(rows)
    for row in result:
        row["mask"] = str(row["mask"])
    return result


def _current_macs(rows) -> list[dict]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("Malformed MAC membership")
    result = []
    addresses = set()
    rule_ids = set()
    for row in rows:
        _known_fields(row, {"name", "macAddress", "ruleId"})
        address = canonical_mac(row.get("macAddress"))
        if address in addresses:
            raise ValueError("Ambiguous current MAC identity")
        addresses.add(address)
        if row.get("name") is not None:
            _text(row["name"], blank=True)
        rule = row.get("ruleId")
        if rule is not None:
            if type(rule) not in (str, int) or rule == "" or (type(rule) is int and rule < 0):
                raise ValueError("Unsupported MAC rule ID")
            key = (type(rule), rule)
            if key in rule_ids:
                raise ValueError("Ambiguous MAC rule ID")
            rule_ids.add(key)
        result.append({key: deepcopy(value) for key, value in row.items() if key in {"name", "macAddress", "ruleId"}})
    return result


def _current_ports(rows) -> list[str]:
    if not isinstance(rows, list):
        raise TypeError("Malformed port membership")
    _ports([parse_port(row) for row in rows])
    return deepcopy(rows)


def group_payload(profile: GroupProfile) -> dict[str, Any]:
    """Validate a writable current target and map the observed UI serializer."""
    raw = profile.raw_data
    _known_fields(raw, _FIELDS)
    _response_metadata(raw)
    identifier = _safe_id(raw.get("groupId"))
    if type(raw.get("type")) is not int:
        raise ValueError("Malformed group kind")
    try:
        kind = GroupType(raw["type"])
    except ValueError as error:
        raise ValueError("Unsupported group kind") from error
    count = raw.get("count")
    if count is not None and (type(count) is not int or count < 0):
        raise ValueError("Malformed group count metadata")
    # Installed UI uses count || null. Keep that specific, source-evidenced normalization.
    result = {"id": identifier, "type": int(kind), "name": _name(raw.get("name")), "count": count or None,
              "ipList": None, "portList": None, "macAddressList": None}
    active = {GroupType.IP: {"ipList"}, GroupType.IP_PORT: {"ipList", "portList"}, GroupType.MAC: {"macAddressList"}}[kind]
    for key in {"ipList", "portList", "macAddressList"} - active:
        if raw.get(key) not in (None, []):
            raise ValueError("Unsupported inactive group membership")
    if "ipList" in active:
        rows = raw.get("ipList")
        if rows is None and kind == GroupType.IP_PORT:
            rows = []
        result["ipList"] = _current_ip_payload(rows, kind)
    if "portList" in active:
        result["portList"] = _current_ports(raw.get("portList"))
    if "macAddressList" in active:
        result["macAddressList"] = _current_macs(raw.get("macAddressList"))
    _protect(result)
    return result


def _protect(payload: dict) -> None:
    rows = payload.get("ipList")
    if rows and rows[0]["ip"] == "0.0.0.0":
        raise ValueError("Protected built-in first-IP group signature")


def _conflicts(name: str, inventory, identity=None) -> None:
    for profile in inventory:
        if identity and (profile.group_type, profile.id) == (identity.group_type, identity.id):
            continue
        if _name(profile.name) == name:
            raise ValueError("Group name conflicts with an existing group")


def _normal_members(key: str, rows) -> list:
    if rows is None:
        return []
    if key == "ipList":
        values = _current_ips(rows, GroupType.IP_PORT)
    elif key == "portList":
        values = _ports([parse_port(row) for row in rows])
    else:
        values = []
        for row in rows:
            value = {"macAddress": canonical_mac(row["macAddress"])}
            if "name" in row:
                value["name"] = row["name"]
            if "ruleId" in row:
                value["ruleId"] = row["ruleId"]
            values.append(value)
    return sorted(json.dumps(row, sort_keys=True) for row in values)


def same_group_content(expected: dict, actual: dict, *, new_macs: set[str] | None = None) -> bool:
    actual = deepcopy(actual)
    if new_macs:
        for row in actual.get("macAddressList") or []:
            if canonical_mac(row["macAddress"]) in new_macs:
                row.pop("ruleId", None)
    scalar_fields = ("id", "type", "name", "count")
    if any(expected.get(key) != actual.get(key) for key in scalar_fields):
        return False
    return all(_normal_members(key, expected.get(key)) == _normal_members(key, actual.get(key))
               for key in ("ipList", "portList", "macAddressList"))


def _membership(request, kind: GroupType, payload: dict, *, create: bool) -> None:
    if kind != GroupType.MAC and request.subnets is not None:
        payload["ipList"] = _ips(request.subnets, kind)
    if kind == GroupType.IP_PORT and request.ports is not None:
        payload["portList"] = _ports(request.ports)
    if kind == GroupType.MAC and request.members is not None:
        payload["macAddressList"] = _macs(request.members, () if create else payload["macAddressList"])


def _warnings(payload: dict | None) -> tuple[str, ...]:
    result = ("Group changes may affect existing consumers; references have not been audited.",)
    if payload and payload["type"] == 1 and not payload["ipList"]:
        result += ("No IP restriction: this IP-port group applies to any IP address.",)
    return result


def build_group_create(request: GroupCreate, inventory: Sequence[GroupProfile]) -> GroupPreview:
    validate_inventory(inventory)
    kind = _CREATE_TYPES.get(type(request))
    if kind is None:
        raise ValueError("Expected a supported create request")
    if any(value is None for key, value in vars(request).items() if key != "name"):
        raise ValueError("Create requires explicit membership collections")
    name = _name(request.name)
    _conflicts(name, inventory)
    payload = {"id": None, "name": name, "type": int(kind), "count": None,
               "ipList": None, "portList": None, "macAddressList": None}
    _membership(request, kind, payload, create=True)
    _protect(payload)
    return GroupPreview("create", None, None, payload, warnings=_warnings(payload))


def build_group_update(identity: GroupIdentity, request: GroupUpdate, inventory: Sequence[GroupProfile]) -> GroupPreview:
    profile = selected_group(identity, inventory)
    if _UPDATE_TYPES.get(type(request)) != identity.group_type:
        raise ValueError("Update request does not match the bound group kind")
    if all(value is None for value in vars(request).values()):
        raise ValueError("No group settings supplied")
    before = deepcopy(profile.raw_data)
    current = group_payload(profile)
    payload = deepcopy(current)
    if request.name is not None:
        payload["name"] = _name(request.name)
    _conflicts(payload["name"], inventory, identity)
    _membership(request, identity.group_type, payload, create=False)
    for key in ("ipList", "portList", "macAddressList"):
        if _normal_members(key, current[key]) == _normal_members(key, payload[key]):
            payload[key] = current[key]
    _protect(payload)
    return GroupPreview("update", identity, before, payload, same_group_content(current, payload), _warnings(payload))


def build_group_delete(identity: GroupIdentity, inventory: Sequence[GroupProfile]) -> GroupPreview:
    profile = selected_group(identity, inventory)
    group_payload(profile)
    return GroupPreview("delete", identity, deepcopy(profile.raw_data), None)
