"""
Definitions for Omada device objects

APs, Switches and Routers
"""
from abc import ABC, abstractmethod, abstractproperty
from typing import Any, List, Optional, Union
from .definitions import (
    BandwidthControl,
    DeviceStatus,
    DeviceStatusCategory,
    Eth802Dot1X,
    GatewayPortMode,
    GatewayPortType,
    LinkDuplex,
    LinkSpeed,
    LinkStatus,
    OmadaApiData,
    PoEMode,
    PortType,
    LedSetting,
)

class OmadaDevice(OmadaApiData):
    """Details of a device connected to the controller"""

    @property
    def type(self) -> str:
        """The type of the device. Its value can be "ap", "gateway", and "switch"."""
        return self._data["type"]

    @property
    def resource_path(self):
        """The API path for querying detailed data about this device"""
        types = {
            "ap": "eaps",
            "gateway": "gateways",
            "switch": "switches"
        }
        return f"{types[self.type]}/{self.mac}"

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
        return DeviceStatus(self._data["status"])

    @property
    def status_category(self) -> DeviceStatusCategory:
        """The high-level status of the device."""
        return DeviceStatusCategory(self._data["statusCategory"])

    @property
    def ip_address(self) -> str:
        """IP address of the device."""
        return self._data["ip"]

    @property
    def display_uptime(self) -> Optional[str]:
        """Uptime of the device, as a display string"""
        if self._data["statusCategory"] == DeviceStatusCategory.CONNECTED:
            return self._data["uptime"]
        else:
            return None

    @property
    def cpu_usage(self) -> int:
        if self._data["statusCategory"] == DeviceStatusCategory.CONNECTED:
            return self._data["cpuUtil"]
        else:
            return 0

    @property
    def mem_usage(self) -> int:
        if self._data["statusCategory"] == DeviceStatusCategory.CONNECTED:
            return self._data["memUtil"]
        else:
            return 0

    @property
    def uptime(self) -> int:
        """Uptime of the device, as a display string"""
        if self._data["statusCategory"] == DeviceStatusCategory.CONNECTED:
            return self._data["uptimeLong"]
        else:
            return 0

    @property
    def firmware_version(self) -> str:
        """Firmware version of the device"""
        return self._data["firmwareVersion"]


class OmadaListDevice(OmadaDevice):
    """An Omada Device (router, switch, eap) as represented in the device list"""

    @property
    def need_upgrade(self) -> bool:
        """True, if a firmware upgrade is available for the device."""
        if self._data["statusCategory"] == DeviceStatusCategory.CONNECTED:
            return self._data.get("needUpgrade", False)
        else:
            return False

    @property
    def fw_download(self) -> bool:
        """True, if a firmware upgrade is being downloaded."""
        if self._data["statusCategory"] == DeviceStatusCategory.CONNECTED:
            return self._data.get("fwDownload", False)
        else:
            return False

class OmadaDetailedDevice(OmadaDevice):
    """Generic properties for Omada Devices (router, switch, eap) as returned by one of the device-type specific endpoints"""

    @property
    def led_setting(self) -> LedSetting:
        """The onboard LED setting for the device"""
        return LedSetting(self._data["ledSetting"])


class OmadaLink(OmadaApiData):
    """Up/Downlink connection from a switch/ap device."""

    @property
    def mac(self) -> str:
        """The MAC of the linked device."""
        return self._data.get("mac", self._data.get("uplinkMac"))

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

class OmadaPortStatus(ABC):
    @property
    @abstractmethod
    def link_status(self) -> LinkStatus:
        """Port's link status."""
        pass

    @property
    @abstractmethod
    def link_speed(self) -> LinkSpeed:
        """Port's link speed."""
        pass

    @property
    @abstractmethod
    def bytes_tx(self) -> int:
        """Number of bytes transmitted by the port."""
        pass

    @property
    @abstractmethod
    def bytes_rx(self) -> int:
        """Number of bytes received by the port."""
        pass

    @property
    @abstractmethod
    def poe_active(self) -> bool:
        """Is the port powering a PoE device?"""
        pass



class OmadaSwitchPortStatus(OmadaApiData, OmadaPortStatus):
    """Status information for a switch port."""

    @property
    def link_status(self) -> LinkStatus:
        """Port's link status."""
        return LinkStatus(self._data["linkStatus"])

    @property
    def link_speed(self) -> LinkSpeed:
        """Port's link speed."""
        return LinkSpeed(self._data["linkSpeed"])

    @property
    def poe_active(self) -> bool:
        """Is the port powering a PoE device?"""
        return self._data["poe"]

    @property
    def poe_power(self) -> Optional[float]:
        """Power (W) supplied over PoE."""
        return self._data.get("poePower")

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
    def port_status(self) -> OmadaSwitchPortStatus:
        """Status of the port."""
        return OmadaSwitchPortStatus(self._data["portStatus"])


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


class OmadaSwitch(OmadaDetailedDevice):
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


class OmadaAccessPoint(OmadaDetailedDevice):
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

    @property
    def wired_uplink(self) -> Optional[OmadaUplink]:
        """ Wired Uplink device for this ap. """
        uplink = self._data.get("wiredUplink", None)
        if uplink is None:
            return None
        return OmadaUplink(uplink)        

class OmadaSwitchPortDetails(OmadaSwitchPort):
    """Full details of a port on a switch."""

    @property
    def port_id(self) -> str:
        """The ID of the port"""
        return self._data["id"]

    @property
    def max_speed(self) -> LinkSpeed:
        """The max speed of the port."""
        return LinkSpeed(self._data["maxSpeed"])

    @property
    def link_speed(self) -> LinkSpeed:
        """The link speed of the port."""
        return LinkSpeed(self._data["linkSpeed"])

    @property
    def duplex(self) -> LinkDuplex:
        """The link duplex state of the port."""
        return LinkDuplex(self._data['duplex'])

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
        return PoEMode(self._data.get("poe", PoEMode.NONE))

    @property
    def bandwidth_limit_mode(self) -> BandwidthControl:
        """Type of bandwidth control applied."""
        return BandwidthControl(self._data["bandWidthCtrlType"])

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
        return Eth802Dot1X(self._data["dot1x"])

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
        return PoEMode(self._data.get("poe", PoEMode.NONE))

    @property
    def bandwidth_limit_mode(self) -> BandwidthControl:
        """Type of bandwidth control applied."""
        return BandwidthControl(self._data["bandWidthCtrlType"])

    @property
    def eth_802_1x_control(self) -> Eth802Dot1X:
        """802.1x Auth mode"""
        return Eth802Dot1X(self._data["dot1x"])

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

class OmadaGatewayPortStatus(OmadaApiData, OmadaPortStatus):
    

    @property
    def port_number(self) -> int:
        return self._data["port"]

    @property
    def name(self) -> str:
        """Port name"""
        return self._data["name"]
    
    @property
    def display_name(self) -> str:
        """Port display name"""
        return self._data.get("portDesc", self.name)

    @property
    def type(self) -> GatewayPortType:
        """Type of the port - SFP, WAN, WAN/LAN or LAN only."""
        return GatewayPortType(self._data["type"])

    @property
    def mode(self) -> GatewayPortMode:
        """Whether the port is operating in WAN or LAN mode"""
        return GatewayPortMode(self._data["mode"])

    @property
    def link_status(self) -> LinkStatus:
        """Low level connectivity status of the link."""
        return LinkStatus(self._data["status"])

    @property
    def bytes_tx(self) -> int:
        """Number of bytes transmitted by the port."""
        return self._data["tx"]

    @property
    def bytes_rx(self) -> int:
        """Number of bytes received by the port."""
        return self._data["rx"]
    
    @property
    def poe_active(self) -> bool:
        return self._data.get("poe", 0) != 0
    
    @property
    def wan_connected(self) -> bool:
        """True if the port is connected to the internet/WAN"""
        return self._data.get("internetState", 0) != 0
    
    @property
    def ipv6_wan_connected(self) -> bool:
        """True if the port is connected to the internet/WAN with IPv6"""
        return dict[str,Any](self._data.get("wanPortIpv6Config", {})).get("internetState", 0) != 0
    
    @property
    def online_detection(self) -> bool:
        """True regular internet ping tests are working"""
        return (self.wan_connected or self.ipv6_wan_connected) and self._data.get("onlineDetection", 0) != 0

    @property
    def ip(self) -> Union[str, None]:
        """DEPRECATED: The WAN IP of the port (for WAN ports only)"""
        return self._data.get("ip")

    @property
    def wan_ip_address(self) -> Union[str, None]:
        """The WAN IPv4 Address of the port (for WAN ports only)"""
        return self._data.get("ip")

    @property
    def wan_ipv6_enabled(self) -> bool:
        """The WAN IPv6 Address of the port (for WAN ports only)"""
        return dict[str,Any](self._data.get("wanPortIpv6Config", {})).get("enable", 0) != 0

    @property
    def wan_ipv6_address(self) -> Union[str, None]:
        """The WAN IPv6 Address of the port (for WAN ports only)"""
        return dict[str,Any](self._data.get("wanPortIpv6Config", {})).get("addr")

    @property
    def link_speed(self) -> LinkSpeed:
        """The established link speed of the port"""
        return LinkSpeed(self._data.get("speed", LinkSpeed.SPEED_10_MBPS))

    @property
    def link_duplex(self) -> LinkDuplex:
        """Actual duplex mode of the port"""
        return LinkDuplex(self._data.get("duplex", LinkDuplex.FULL))

    @property
    def wan_protocol(self) -> Union[str, None]:
        """May be: static, dhcp, pppoe, l2tp, pptp """
        return self._data.get("proto")

    # For connected ports
    #"rxPkt":217028151,"rxPktRate":35,"rxRate":6,"tx":15157457326,"txPkt":60843861,"txPktRate":24,"txRate":5,
    # "mirroredPorts":[]

    # FOR WAN PORTS:
    # "wanPortIpv6Config":{"enable":0,"addr":"","gateway":"","priDns":"","sndDns":"","internetState":0},
    # "wanPortIpv4Config":{"ip":"x.x.x.x","gateway":"x.x.x.x","gateway2":"0.0.0.0","priDns":"194.168.4.100","sndDns":"194.168.8.100","priDns2":"0.0.0.0","sndDns2":"0.0.0.0"}


class OmadaGatewayPortConfig(OmadaApiData):

    def __init__(self, data: dict, poe_enabled: Union[bool, None]):
        super().__init__(data)
        self._poe_enabled = poe_enabled

    @property
    def port_number(self) -> int:
        """Port number"""
        return self._data["port"]

    @property
    def duplex(self) -> LinkDuplex:
        """Configured duplex mode for the port."""
        return self._data.get("duplex", LinkDuplex.AUTO)

    @property
    def link_speed(self) -> LinkSpeed:
        """Configured link speed for the port."""
        return self._data.get("linkSpeed", LinkSpeed.SPEED_AUTO)

    @property
    def mirror_enable(self) -> bool:
        """True if port mirroring is enabled"""
        return self._data.get("mirrorEnable", False)

    @property
    def port_status(self) -> OmadaGatewayPortStatus:
        """Full status of the port"""
        return OmadaGatewayPortStatus(self._data["portStat"])
    
    @property
    def poe_mode(self) -> PoEMode:
        """PoE mode for the port"""
        poe_mode_mapping = {
            True: PoEMode.ENABLED,
            False: PoEMode.DISABLED,
            None: PoEMode.NONE
        }

        return poe_mode_mapping[self._poe_enabled]

class OmadaGateway(OmadaDetailedDevice):

    @property
    def number_of_ports(self) -> int:
        """The number of ports on the switch."""
        return self._data.get("portNum", 0)

    @property
    def supports_poe(self) -> bool:
        """True if the device supports PoE."""
        return self._data["supportPoe"]

    @property
    def ip(self) -> str:
        """Gateway's LAN IP address."""
        return self._data["ip"]

    @property
    def port_status(self) -> List[OmadaGatewayPortStatus]:
        """Status of the gateway's ports."""
        return [
            OmadaGatewayPortStatus(p) for p in self._data["portStats"]
        ]

    @property
    def port_configs(self) -> List[OmadaGatewayPortConfig]:
        """Configuration of the gateway's ports. Also includes status..."""

        poeData = {}
        if self.supports_poe:
            # Combined Gateway+PoE switch has this extra data
            poeData = {int(x["portId"]): bool(x["enable"]) for x in self._data["poeSettings"]}

        return [
            OmadaGatewayPortConfig(p, poeData.get(p["port"])) for p in self._data["portConfigs"]
        ]
    
    @property
    def lldp_enabled(self) -> bool:
        """LLDP Enabled for the whole gateway"""
        return self._data.get("lldpEnable", False)
    
    @property
    def echo_server(self) -> Union[str, None]:
        return self._data.get("echoServer")

    @property
    def is_combined_gateway(self) -> bool:
        """True if this is a combined gateway/switch."""
        return self._data.get("combinedGateway", False)


