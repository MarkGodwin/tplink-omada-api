"""Conservative VLAN-only write contract verified on controller 5.15.8.12."""

from copy import deepcopy
from dataclasses import dataclass

from .networks import LanNetwork

# These fields describe identity, binding or references in the list response;
# the installed VLAN-only editor does not send them in its write payload.
_COMPUTED_FIELDS = {
    "id", "site", "interfaceIds", "portal", "accessControlRule", "rateLimit", "allLan",
    "resource", "origName", "interface", "primary",
}
_WRITABLE_FIELDS = {
    "name", "purpose", "application", "vlan", "dhcpL2RelayEnable", "igmpSnoopEnable",
    "fastLeaveEnable", "mldSnoopEnable", "dhcpGuard", "dhcpv6Guard",
}
_GUARD_SERVERS = {
    "dhcpGuard": {"dhcpSvr1", "dhcpSvr2"},
    "dhcpv6Guard": {"dhcpv6Svr1", "dhcpv6Svr2"},
}
_BOOLEAN_FIELDS = {"dhcpL2RelayEnable", "igmpSnoopEnable", "fastLeaveEnable", "mldSnoopEnable"}


def _name(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or not value.isprintable() or len(value.strip().encode("utf-8")) > 128:
        raise ValueError("VLAN name must contain 1–128 UTF-8 bytes and no control characters")
    if value.strip().casefold() in {"default", "management", "management(default)"}:
        raise ValueError("Default/management VLAN names are protected")
    return value.strip()


def _vlan_id(value: int | None) -> int:
    if type(value) is not int or not 1 <= value <= 4090:
        raise ValueError("VLAN ID must be an integer from 1 to 4090")
    if value == 1:
        raise ValueError("VLAN 1 is protected")
    return value


def validate_vlan_target(network: LanNetwork) -> None:
    """Reject protected, routed, incomplete and unverified VLAN targets."""
    raw = network.raw_data
    identity = raw.get("id")
    if not isinstance(identity, str) or not identity or not identity.isascii() or any(not (c.isalnum() or c in "-_") for c in identity):
        raise ValueError("Missing or unsafe VLAN network identity")
    primary = raw.get("primary")
    if (
        network.purpose != "vlan" or not isinstance(primary, bool) or primary
        or type(raw.get("application")) is not int or raw["application"] != 0
    ):
        raise ValueError("Only non-primary VLAN-only networks with application=0 can be changed")
    _vlan_id(network.vlan_id)
    _name(network.name)
    unknown = raw.keys() - _COMPUTED_FIELDS - _WRITABLE_FIELDS
    if unknown:
        raise ValueError(f"Unsupported VLAN fields: {', '.join(sorted(unknown))}")
    if any(field in raw and type(raw[field]) is not bool for field in _BOOLEAN_FIELDS):
        raise ValueError("Invalid VLAN boolean settings")
    for field, servers in _GUARD_SERVERS.items():
        if field not in raw:
            continue
        guard = raw[field]
        if not isinstance(guard, dict) or type(guard.get("enable")) is not bool:
            raise ValueError(f"Invalid VLAN {field}: expected a guard with boolean enable")
        unknown = guard.keys() - servers - {"enable"}
        if unknown:
            raise ValueError(f"Unsupported VLAN fields in {field}: {', '.join(sorted(unknown))}")
        if any(guard.get(server) is not None and not isinstance(guard[server], str) for server in servers):
            raise ValueError(f"Invalid VLAN {field}: server values must be strings or null")


def validate_vlan_conflicts(payload: dict, networks: list[LanNetwork], exclude_id: str | None = None) -> None:
    """Reject collisions against fresh inventory, including routed networks."""
    try:
        vlan_id = int(payload["vlan"] if "vlan" in payload else payload["vlans"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Invalid VLAN payload identifier") from error
    name = payload["name"].casefold()
    for network in networks:
        identity = network.raw_data.get("id")
        if not isinstance(identity, str) or not identity:
            raise ValueError("LAN inventory contains a missing or invalid network identity")
        if exclude_id is not None and identity == exclude_id:
            continue
        if network.vlan_id == vlan_id or network.name.casefold() == name:
            raise ValueError("VLAN ID or name already exists")


def resolve_vlan_target(target: str, networks: list[LanNetwork], *, by_id: bool = False) -> LanNetwork:
    """Resolve an exact ID/name, or strictly an ID after an earlier selection."""
    matches = [n for n in networks if n.raw_data.get("id") == target or (not by_id and n.raw_data.get("name") == target)]
    if len(matches) != 1:
        raise ValueError("VLAN target is missing or ambiguous; use an exact network ID")
    identity = matches[0].raw_data.get("id")
    if sum(n.raw_data.get("id") == identity for n in networks) != 1:
        raise ValueError("VLAN target identity is ambiguous; inspect controller inventory")
    return matches[0]


@dataclass(frozen=True)
class VlanCreate:
    """Create a single VLAN-only network; does not configure routing or DHCP."""

    name: str
    vlan_id: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _name(self.name))
        _vlan_id(self.vlan_id)

    def payload(self) -> dict:
        """Return the range-string create payload used by the installed editor."""
        return {
            "application": 0,
            "name": self.name,
            "purpose": "vlan",
            "vlans": str(self.vlan_id),
            "dhcpL2RelayEnable": False,
            "igmpSnoopEnable": False,
            "mldSnoopEnable": False,
            "dhcpGuard": {"enable": False, "dhcpSvr1": None, "dhcpSvr2": None},
            "dhcpv6Guard": {"enable": False, "dhcpv6Svr1": None, "dhcpv6Svr2": None},
        }


@dataclass(frozen=True)
class VlanUpdate:
    """Change name and/or VLAN ID while preserving existing writable settings."""

    name: str | None = None
    vlan_id: int | None = None

    def __post_init__(self) -> None:
        if self.name is None and self.vlan_id is None:
            raise ValueError("At least one VLAN change is required")
        if self.name is not None:
            object.__setattr__(self, "name", _name(self.name))
        if self.vlan_id is not None:
            _vlan_id(self.vlan_id)

    def payload(self, network: LanNetwork) -> dict:
        """Merge verified writable settings into a defensive copy."""
        validate_vlan_target(network)
        payload = {k: deepcopy(v) for k, v in network.raw_data.items() if k not in _COMPUTED_FIELDS}
        if self.name is not None:
            payload["name"] = self.name
        if self.vlan_id is not None:
            payload["vlan"] = self.vlan_id
        return payload
