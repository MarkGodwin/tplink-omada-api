"""
Definitions for Omada device objects

APs, Switches and Routers
"""
from typing import Any, List, Optional
from .definitions import (
    BandwidthControl,
    DeviceStatus,
    DeviceStatusCategory,
    Eth802Dot1X,
    LinkSpeed,
    LinkStatus,
    PoEMode,
    PortType,
)

class OmadaApiData:
    def __init__(self, data: dict[str, Any]):
        self._data = data

    @property
    def raw_data(self) -> dict[str, Any]:
        return self._data


class OmadaDevice(OmadaApiData):
    """Details of a device connected to the controller"""

    @property
    def type(self) -> str:
        """The type of the device. Its value can be "ap", "gateway", and "switch"."""
        return self._data["type"]

    @property
    def mac(self) -> str:
        """The MAC address of the device."""
        return self._data["mac"]

    @property
    def name(self) -> str:
        """The device name."""
        return self._data["name"]

    @property
    def model(self) -> str:
        """The device model, such as EAP225."""
        return self._data["model"]

    @property
    def model_display_name(self) -> str:
        """Model description for front-end display."""
        return self._data["showModel"]

    @property
    def status(self) -> DeviceStatus:
        """The status of the device."""
        return self._data["status"]

    @property
    def status_category(self) -> DeviceStatusCategory:
        """The high-level status of the device."""
        return self._data["statusCategory"]

    @property
    def ip_address(self) -> str:
        """IP address of the device."""
        return self._data["ip"]

    @property
    def display_uptime(self) -> str:
        """Uptime of the device, as a display string"""
        return self._data["uptime"]

    @property
    def uptime(self) -> int:
        """Uptime of the device, as a display string"""
        return self._data["uptimeLong"]

    @property
    def firmware_version(self) -> str:
        """Firmware version of the device"""
        return self._data["firmwareVersion"]


class OmadaListDevice(OmadaDevice):
    """An Omada Device (router, switch, eap) as represented in the device list"""

    @property
    def need_upgrade(self) -> bool:
        """True, if a firmware upgrade is available for the device."""
        return self._data["needUpgrade"]

    @property
    def fw_download(self) -> bool:
        """True, if a firmware upgrade is being downloaded."""
        return self._data["fwDownload"]


class OmadaLink(OmadaApiData):
    """Up/Downlink connection from a switch/ap device."""

    @property
    def mac(self) -> str:
        """The MAC of the linked device."""
        return self._data["mac"]

    @property
    def name(self) -> str:
        """The name of the linked device."""
        return self._data["name"]

    @property
    def type(self) -> str:
        """The type of device linked to."""
        return self._data["type"]

    @property
    def port(self) -> int:
        """The port's number."""
        return self._data["port"]


class OmadaDownlink(OmadaLink):
    """Downlink connection from a switch/ap port."""

    @property
    def type(self) -> str:
        """The type of device downlinked to."""
        return "ap"

    @property
    def model(self) -> str:
        """The model name of device linked to."""
        return self._data["model"]


class OmadaUplink(OmadaLink):
    """Uplink connection from a switch/ap device."""


class OmadaPortStatus(OmadaApiData):
    """Status information for a switch port."""

    @property
    def link_status(self) -> LinkStatus:
        """Port's link status."""
        return self._data["linkStatus"]

    @property
    def link_speed(self) -> LinkSpeed:
        """Port's link speed."""
        return self._data["linkSpeed"]

    @property
    def poe_active(self) -> bool:
        """Is the port powering a PoE device?"""
        return self._data["poe"]

    @property
    def poe_power(self) -> float:
        """Power (W) supplied over PoE."""
        if "poePower" in self._data:
            return self._data["poePower"]
        return 0.0

    @property
    def bytes_tx(self) -> int:
        """Number of bytes transmitted by the port."""
        return self._data["tx"]

    @property
    def bytes_rx(self) -> int:
        """Number of bytes received by the port."""
        return self._data["rx"]

    @property
    def stp_discarding(self) -> bool:
        """Stp blocking status in spanning tree."""
        return self._data["stpDiscarding"]


class OmadaSwitchPort(OmadaApiData):
    """Port on a switch/gateway device."""

    @property
    def port(self) -> int:
        """The port's number."""
        return self._data["port"]

    @property
    def name(self) -> str:
        """The device name."""
        return self._data["name"]

    @property
    def profile_id(self) -> str:
        """ID of the port's config profile."""
        return self._data["profileId"]

    @property
    def type(self) -> PortType:
        """The type of the port."""
        return self._data["type"]

    @property
    def operation(self) -> str:
        """Port config: switching, mirroring or aggregating."""
        return self._data["operation"]

    @property
    def is_disabled(self) -> bool:
        """Is the port disabled?"""
        return self._data["disable"]

    @property
    def port_status(self) -> OmadaPortStatus:
        """Status of the port."""
        return OmadaPortStatus(self._data["portStatus"])


class OmadaSwitchDeviceCaps(OmadaApiData):
    """Capabilities of a switch."""

    @property
    def poe_ports(self) -> int:
        """Number of PoE ports supported."""
        return self._data["poePortNum"]

    @property
    def supports_poe(self) -> bool:
        """Is PoE supported."""
        return self._data["poeSupport"]

    @property
    def supports_bt(self) -> bool:
        """Is BT supported."""
        return self._data["supportBt"]


class OmadaSwitch(OmadaDevice):
    """Details of a switch connected to the controller."""

    @property
    def number_of_ports(self) -> int:
        """The number of ports on the switch."""
        if "portNum" in self._data:
            return self._data["portNum"]
        # So much for the docs
        return self._data["deviceMisc"]["portNum"]

    @property
    def ports(self) -> List[OmadaSwitchPort]:
        """List of ports attached to the switch."""
        return [OmadaSwitchPort(p) for p in self._data["ports"]]

    @property
    def uplink(self) -> Optional[OmadaUplink]:
        """ Uplink device for this switch. """
        if not "uplink" in self._data:
            return None
        uplink = self._data["uplink"]
        if uplink is None:
            return None
        return OmadaUplink(uplink)

    @property
    def downlink(self) -> List[OmadaDownlink]:
        """Downlink devices attached to switch."""
        if "downlinkList" in self._data:
            return [OmadaDownlink(d) for d in self._data["downlinkList"]]
        return []

    @property
    def device_capabilities(self) -> OmadaSwitchDeviceCaps:
        """Capabilities of the switch."""
        return OmadaSwitchDeviceCaps(self._data["devCap"])


class OmadaAccesPointLanPortSettings(OmadaApiData):
    """A LAN port on an access point."""

    @property
    def port_name(self) -> str:
        """Name of the port - can't be edited"""
        return self._data["lanPort"]

    @property
    def supports_vlan(self) -> bool:
        """True if the port supports VLAN tagging"""
        return self._data["supportVlan"]

    @property
    def local_vlan_enable(self) -> bool:
        """True if VLAN tagging is enabled for the port explicitly"""
        return self._data["localVlanEnable"]

    @property
    def local_vlan_id(self) -> int:
        """VLAN ID for this port"""
        return self._data["localVlanId"]

    @property
    def supports_poe(self) -> bool:
        """True if the port supports PoE output"""
        return self._data["supportPoe"]

    @property
    def poe_enable(self) -> bool:
        """
        True to enable PoE.

        WARNING: Do not enable PoE for EAPs powered from another EAP
        """
        return self._data["poeOutEnable"]


class OmadaAccessPoint(OmadaDevice):
    """Details of an Access Point connected to the controller."""

    @property
    def wireless_linked(self) -> bool:
        """True, if the AP is connected wirelessley."""
        return self._data["wirelessLinked"]

    @property
    def supports_5g(self) -> bool:
        """True if 5G wifi is supported"""
        return self._data["deviceMisc"]["support5g"]

    @property
    def supports_5g2(self) -> bool:
        """True if 5G2 wifi is supported"""
        return self._data["deviceMisc"]["support5g2"]

    @property
    def supports_6g(self) -> bool:
        """True if Wifi 6 is supported"""
        return self._data["deviceMisc"]["support6g"]

    @property
    def supports_11ac(self) -> bool:
        """True if PoE is supported"""
        return self._data["deviceMisc"]["support11ac"]

    @property
    def supports_mesh(self) -> bool:
        """True if mesh networking is supported"""
        return self._data["deviceMisc"]["supportMesh"]

    @property
    def lan_port_settings(self) -> List[OmadaAccesPointLanPortSettings]:
        """Settings for the LAN ports on the access point"""
        return [
            OmadaAccesPointLanPortSettings(p) for p in self._data["lanPortSettings"]
        ]


class OmadaSwitchPortDetails(OmadaSwitchPort):
    """Full details of a port on a switch."""

    @property
    def port_id(self) -> str:
        """The ID of the port"""
        return self._data["id"]

    @property
    def max_speed(self) -> LinkSpeed:
        """The max speed of the port."""
        return self._data["maxSpeed"]

    @property
    def profile_name(self) -> str:
        """Name of the port's config profile"""
        return self._data["profileName"]

    @property
    def has_profile_override(self) -> bool:
        """True if the port's config profile has been overridden."""
        return self._data["profileOverrideEnable"]

    @property
    def poe_mode(self) -> PoEMode:
        """PoE config for this port."""
        return self._data["poe"]

    @property
    def bandwidth_limit_mode(self) -> BandwidthControl:
        """Type of bandwidth control applied."""
        return self._data["bandWidthCtrlType"]

    # "bandCtrl": {
    #     "egressEnable": false,
    #     "egressLimit": 0,
    #     "egressUnit": 1,
    #     "ingressEnable": false,
    #     "ingressLimit": 0,
    #     "ingressUnit": 1
    # },
    # "stormCtrl": {
    #     "unknownUnicastEnable": false,
    #     "unknownUnicast": 0,
    #     "multicastEnable": false,
    #     "multicast": 0,
    #     "broadcastEnable": false,
    #     "broadcast": 0,
    #     "action": 0,
    #     "recoverTime": 3600
    # },

    @property
    def eth_802_1x_control(self) -> Eth802Dot1X:
        """802.1x Auth mode"""
        return self._data["dot1x"]

    @property
    def lldp_med_enabled(self) -> bool:
        """LLDP Mode"""
        return self._data["lldpMedEnable"]

    @property
    def topology_notify_enabled(self) -> bool:
        """Topology notify mode"""
        return self._data["topoNotifyEnable"]

    @property
    def spanning_tree_enabled(self) -> bool:
        """Spanning tree loopback control"""
        return self._data["spanningTreeEnable"]

    @property
    def loopback_detect_enabled(self) -> bool:
        """Loopback detection"""
        return self._data["loopbackDetectEnable"]

    @property
    def port_isolation_enabled(self) -> bool:
        """Port isolation (Danger!)"""
        return self._data["portIsolationEnable"]


class OmadaPortProfile(OmadaApiData):
    """Definition of a switch port configuration profile."""

    @property
    def profile_id(self) -> str:
        """ID of this profile."""
        return self._data["id"]

    @property
    def site(self) -> str:
        """Site which this profile is valid for."""
        return self._data["site"]

    @property
    def name(self) -> str:
        """Name of the profile."""
        return self._data["name"]

    @property
    def poe_mode(self) -> PoEMode:
        """PoE mode."""
        return self._data["poe"]

    @property
    def bandwidth_limit_mode(self) -> BandwidthControl:
        """Type of bandwidth control applied."""
        return self._data["bandWidthCtrlType"]

    @property
    def eth_802_1x_control(self) -> Eth802Dot1X:
        """802.1x Auth mode"""
        return self._data["dot1x"]

    @property
    def lldp_med_enabled(self) -> bool:
        """LLDP Mode"""
        return self._data["lldpMedEnable"]

    @property
    def topology_notify_enabled(self) -> bool:
        """Topology notify mode"""
        return self._data["topoNotifyEnable"]

    @property
    def spanning_tree_enabled(self) -> bool:
        """Spanning tree loopback control"""
        return self._data["spanningTreeEnable"]

    @property
    def loopback_detect_enabled(self) -> bool:
        """Loopback detection"""
        return self._data["loopbackDetectEnable"]

    @property
    def port_isolation_enabled(self) -> bool:
        """Port isolation (Danger!)"""
        return self._data["portIsolationEnable"]


class OmadaInterfaceDetails(OmadaApiData):
    """Basic UI Information about controller."""

    @property
    def controller_name(self) -> str:
        """Display name of the controller."""
        return self._data["controllerName"]


class OmadaFirmwareUpdate(OmadaApiData):
    """Status information for a switch port."""

    @property
    def current_version(self) -> str:
        """Device's current firmware version."""
        return self._data["curFwVer"]

    @property
    def latest_version(self) -> str:
        """Latest firmware version available."""
        return self._data["lastFwVer"]

    @property
    def release_notes(self) -> str:
        """Release notes for the new firmware."""
        return self._data["fwReleaseLog"]
