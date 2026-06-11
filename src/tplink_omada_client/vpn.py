"""VPN policy models for the Omada SDN controller (OpenAPI)."""

from enum import StrEnum
from typing import Any

from .definitions import OmadaApiData

# OpenAPI list endpoints per VPN tab (relative to .../sites/{site}/vpn/).
# All three confirmed from captures on controller 6.2.10.18.
VPN_LIST_ENDPOINTS: dict[str, str] = {
    "server": "client-to-site-vpn-servers",  # confirmed
    "client": "client-to-site-vpn-clients",  # confirmed
    "site_to_site": "site-to-site-vpns",     # confirmed
}

# vpnType values seen so far: 2 = IPsec, 3 = OpenVPN.
VPN_TYPE_NAMES: dict[int, str] = {
    2: "IPsec",
    3: "OpenVPN",
}


class OmadaVpnCategory(StrEnum):
    """Which VPN tab a policy belongs to."""

    SERVER = "server"
    CLIENT = "client"
    SITE_TO_SITE = "site_to_site"


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
    def vpn_type(self) -> int:
        """Raw vpnType code (2 = IPsec, 3 = OpenVPN)."""
        return int(self._data.get("vpnType", -1))

    @property
    def vpn_type_name(self) -> str:
        """Human-readable protocol, falling back to the raw code."""
        return VPN_TYPE_NAMES.get(self.vpn_type, f"VPN ({self.vpn_type})")

    @property
    def unique_id(self) -> str:
        """Stable key: category + id."""
        return f"{self._category}_{self.policy_id}"
