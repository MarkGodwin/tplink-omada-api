"""Immutable values for IP, IP-port and MAC group management."""

import re
from dataclasses import dataclass, fields
from enum import IntEnum
from typing import Any, Literal
from urllib.parse import urlsplit


class GroupType(IntEnum):
    """Kinds exposed by the installed group editor."""

    IP = 0
    IP_PORT = 1
    MAC = 2


@dataclass(frozen=True)
class GroupIdentity:
    """A group ID is scoped to its kind and owning site client."""

    group_type: GroupType
    id: str


@dataclass(frozen=True)
class GroupContext:
    """Non-secret controller/site scope, never a portable approval token."""

    controller: str
    controller_id: str
    site_id: str


@dataclass(frozen=True)
class IpSubnet:
    ip: str
    prefix: int


@dataclass(frozen=True)
class PortRange:
    first: int
    last: int


@dataclass(frozen=True)
class MacMember:
    address: str
    name: str | None = None


@dataclass(frozen=True)
class ObservedMacMember:
    """Read-only observed metadata; not accepted as editable request input."""

    address: str
    name: str | None = None
    rule_id: str | int | None = None
    rule_id_present: bool = False
    name_present: bool = False


def _snapshot(request) -> None:
    for item in fields(request):
        value = getattr(request, item.name)
        if item.name in ("subnets", "ports", "members") and value is not None:
            object.__setattr__(request, item.name, tuple(value))


@dataclass(frozen=True)
class IpGroupCreate:
    name: str
    subnets: tuple[IpSubnet, ...]

    def __post_init__(self):
        _snapshot(self)


@dataclass(frozen=True)
class IpGroupUpdate:
    name: str | None = None
    subnets: tuple[IpSubnet, ...] | None = None

    def __post_init__(self):
        _snapshot(self)


@dataclass(frozen=True)
class IpPortGroupCreate:
    name: str
    subnets: tuple[IpSubnet, ...]
    ports: tuple[PortRange, ...]

    def __post_init__(self):
        _snapshot(self)


@dataclass(frozen=True)
class IpPortGroupUpdate:
    name: str | None = None
    subnets: tuple[IpSubnet, ...] | None = None
    ports: tuple[PortRange, ...] | None = None

    def __post_init__(self):
        _snapshot(self)


@dataclass(frozen=True)
class MacGroupCreate:
    name: str
    members: tuple[MacMember, ...]

    def __post_init__(self):
        _snapshot(self)


@dataclass(frozen=True)
class MacGroupUpdate:
    name: str | None = None
    members: tuple[MacMember, ...] | None = None

    def __post_init__(self):
        _snapshot(self)


GroupCreate = IpGroupCreate | IpPortGroupCreate | MacGroupCreate
GroupUpdate = IpGroupUpdate | IpPortGroupUpdate | MacGroupUpdate


@dataclass(frozen=True)
class GroupPreview:
    """Detached proposed state; dictionaries do not alias response/request data."""

    operation: Literal["create", "update", "delete"]
    identity: GroupIdentity | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    no_op: bool = False
    warnings: tuple[str, ...] = ("Group changes may affect existing consumers; references have not been audited.",)
    context: GroupContext | None = None


def _port(item: PortRange) -> str:
    if not isinstance(item, PortRange) or type(item.first) is not int or type(item.last) is not int:
        raise ValueError("Expected integer port endpoints")
    if not 0 <= item.first <= item.last <= 65535:
        raise ValueError("Ports must be ordered within 0..65535")
    return str(item.first) if item.first == item.last else f"{item.first}-{item.last}"


def parse_port(value: str) -> PortRange:
    """Strict parser shared by observed membership and write validation."""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(?:-[0-9]+)?", value.strip()):
        raise ValueError("Expected PORT or LOW-HIGH")
    parts = value.strip().split("-")
    result = PortRange(int(parts[0]), int(parts[-1]))
    _port(result)
    return result


def _safe_controller_endpoint(url: str) -> str:
    """Keep only a controller's scheme/host/port for diagnostics and scope."""
    try:
        parts = urlsplit(url)
        host, port = parts.hostname, parts.port
        if not host or parts.scheme not in ("http", "https"):
            return "[invalid controller endpoint]"
    except ValueError:
        return "[invalid controller endpoint]"
    if ":" in host:
        host = f"[{host}]"
    return f"{parts.scheme}://{host}" + (f":{port}" if port is not None else "")
