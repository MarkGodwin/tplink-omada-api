"""VPN policy models for the Omada SDN controller (OpenAPI)."""

from enum import IntEnum, StrEnum
from typing import Any

from .definitions import OmadaApiData


class OmadaVpnCategory(StrEnum):
    """Which VPN tab a policy belongs to."""

    SERVER = "server"
    CLIENT = "client"
    SITE_TO_SITE = "site_to_site"


# OpenAPI list endpoints per VPN tab (relative to .../sites/{site}/vpn/).
# All three confirmed from captures on controller 6.2.10.18.
_VPN_LIST_ENDPOINTS: dict[OmadaVpnCategory, str] = {
    OmadaVpnCategory.SERVER: "client-to-site-vpn-servers",
    OmadaVpnCategory.CLIENT: "client-to-site-vpn-clients",
    OmadaVpnCategory.SITE_TO_SITE: "site-to-site-vpns",
}


class OmadaVpnType(IntEnum):
    """Known VPN protocol types."""

    UNKNOWN = -1
    L2TP = 0
    PPTP = 1
    IPSEC = 2
    OPENVPN = 3
    WIREGUARD = 4
    SSL = 5

    @classmethod
    def _missing_(cls, _):
        return OmadaVpnType.UNKNOWN


class OmadaVpnPolicy(OmadaApiData):
    """A single VPN entry that can be enabled/disabled via .../vpn/{id}/status."""

    def __init__(self, category: OmadaVpnCategory, data: dict[str, Any]) -> None:
        super().__init__(data)
        self._category = category

    @property
    def category(self) -> OmadaVpnCategory:
        """The VPN tab this policy belongs to."""
        return self._category

    @property
    def policy_id(self) -> str:
        """Controller-side id, used as {id} in the status PATCH."""
        return self._data["id"]

    @property
    def name(self) -> str:
        """User-defined policy name."""
        return self._data.get("name", self.policy_id)

    @property
    def enabled(self) -> bool:
        """Current enabled state (the 'status' flag)."""
        return bool(self._data.get("status", False))

    @property
    def vpn_type(self) -> OmadaVpnType:
        """VPN protocol type."""
        try:
            return OmadaVpnType(int(self._data.get("vpnType", -1)))
        except (TypeError, ValueError):
            return OmadaVpnType.UNKNOWN

    @property
    def vpn_type_name(self) -> str:
        """Human-readable protocol, falling back to the raw code."""
        return {
            OmadaVpnType.IPSEC: "IPsec",
            OmadaVpnType.OPENVPN: "OpenVPN",
            OmadaVpnType.WIREGUARD: "WireGuard",
        }.get(self.vpn_type, self.vpn_type.name)

    @property
    def unique_id(self) -> str:
        """Stable key: category + id."""
        return f"{self._category}_{self.policy_id}"
