"""Definitions for Omada network data objects."""

from .definitions import OmadaApiData


class DhcpReservation(OmadaApiData):
    """DHCP reservation on an Omada controller."""

    @property
    def id(self) -> str:
        """Reservation ID."""
        return self._data["id"]

    @property
    def mac(self) -> str:
        """Device MAC address."""
        return self._data["mac"]

    @property
    def ip(self) -> str:
        """Reserved IP address."""
        return self._data["ip"]

    @property
    def description(self) -> str | None:
        """Description / name for the reservation."""
        return self._data.get("description")

    @property
    def status(self) -> bool | None:
        """Whether the reservation is active."""
        return self._data.get("status")

    @property
    def net_id(self) -> str | None:
        """ID of the network this reservation belongs to."""
        return self._data.get("netId")

    @property
    def net_name(self) -> str | None:
        """Name of the network this reservation belongs to."""
        return self._data.get("netName")

    @property
    def client_name(self) -> str | None:
        """Name of the client associated with this reservation."""
        return self._data.get("clientName")

    @property
    def export_to_ip_mac_binding(self) -> bool | None:
        """Whether to export this reservation to IP-MAC binding."""
        return self._data.get("exportToIpMacBinding")


class LanNetwork(OmadaApiData):
    """LAN network configuration."""

    # Properties defined during vlan-listing implementation


class LanProfile(OmadaApiData):
    """LAN port profile (VLAN profile for switch ports)."""

    # Properties defined during vlan-listing implementation


class GatewayAcl(OmadaApiData):
    """Gateway ACL rule."""

    # Properties defined during acl-listing implementation


class SwitchAcl(OmadaApiData):
    """Switch ACL rule."""

    # Properties defined during acl-listing implementation


class EapAcl(OmadaApiData):
    """EAP (access point) ACL rule."""

    # Properties defined during acl-listing implementation


class GroupProfile(OmadaApiData):
    """Group profile (IP group, MAC group, IP-Port group, etc.)."""

    # Properties defined during ip-groups implementation


class IpMacBinding(OmadaApiData):
    """IP-MAC binding entry."""

    # Properties defined during ip-mac-bindings implementation
