from typing import cast, Optional

from .definitions import (
    AuthenticationStatus,
    ConnectType,
    OmadaApiData,
    RadioId,
    WifiMode,
)

class OmadaNetworkClient(OmadaApiData):
    """Base representation of Omada client"""

    @property
    def connection_time(self) -> Optional[int]:
        """ Client connection time in seconds. """
        if "uptime" in self._data:
            return self._data["uptime"]
        if "duration" in self._data:
            return self._data["duration"]
        return None

    @property
    def is_blocked(self) -> bool:
        # Most API calls return 'blocked' but the 'known_clients' call returns 'block'
        return self._data.get("blocked", self._data.get("block", False))

    @property
    def is_guest(self) -> bool:
        """ Indicates if client is a 'guest'. """
        return self._data["guest"]

    @property
    def last_seen(self) -> float:
        """ Timestamp in second from Unix Epoch when client was last connected. """
        return self._data["lastSeen"] / 1000

    @property
    def mac(self) -> str:
        """ The MAC address of the client. """
        return self._data["mac"]

    @property
    def name(self) -> str:
        """ The name of the client. """
        return self._data["name"]

    @property
    def is_wireless(self) -> Optional[bool]:
        """ Indicates if client is a wireless client """
        return self._data.get("wireless")

class OmadaConnectedClient(OmadaNetworkClient):
    @property
    def is_active(self) -> bool:
        """ Indicates if client is active """
        return self._data["active"]

    @property
    def activity(self) -> int:
        """ Realtime downlink rate (Byte/s) """
        return self._data["activity"]

    @property
    def auth_status(self) -> AuthenticationStatus:
        """ Authentication status """
        return self._data["authStatus"]

    @property
    def connect_dev_type(self) -> Optional[str]:
        """ Connected device type (ap, gateway, switch) """
        return self._data.get("connectDevType")

    @property
    def connect_type(self) -> ConnectType:
        """ Connection type """
        return self._data["connectType"]
    
    @property
    def device_type(self) -> str:
        """ Device type (Android, iPhone, iPod... mostly Unkown) """
        return self._data["deviceType"]

    @property
    def down_packet(self) -> int:
        """ Number of packets sent to client """
        return self._data["downPacket"]

    @property
    def host_name(self) -> Optional[str]:
        """ The client's hostname. """
        return self._data.get("hostName")

    @property
    def ip(self) -> Optional[str]:
        """ The client's IP address. """
        return self._data.get("ip")

    @property
    def traffic_down(self) -> int:
        """ Number of bytes sent to client """
        return self._data["trafficDown"]

    @property
    def traffic_up(self) -> int:
        """ Number of bytes sent by client """
        return self._data["trafficUp"]

    @property
    def up_packet(self) -> int:
        """ Number of packets received from client """
        return self._data["upPacket"]

    @property
    def vlan(self) -> Optional[int]:
        """
        VLAN ID
        
        This property appears to work with some access points but is not provided
        by others.

        Known to work on: EAP653
        Not provided by: EAP660
        """
        return self._data.get("vid")


class IpSetting(OmadaApiData):

    @property
    def used_fixed_addr(self) -> bool:
        return self._data["useFixedAddr"]
    
class RateLimit(OmadaApiData):
    
    @property
    def enabled(self) -> bool:
        return self._data["enable"]

    @property
    def down_enabled(self) -> bool:
        return self._data["downEnable"]

    @property
    def down_limit(self) -> int:
        return self._data["downLimit"]

    @property
    def down_unit(self) -> int:
        return self._data["downUnit"]

    @property
    def up_enabled(self) -> bool:
        return self._data["upEnable"]

    @property
    def up_limit(self) -> int:
        return self._data["upLimit"]


    @property
    def up_unit(self) -> int:
        return self._data["upUnit"]

class OmadaClientDetails(OmadaConnectedClient):

    @property
    def device_category(self) -> Optional[str]:
        return self._data.get("deviceCategory")
    
    @property
    def ip_setting(self) -> IpSetting:
        return IpSetting(self._data["ipSetting"])

    @property
    def os_name(self) -> Optional[str]:
        return self._data.get("osName")

    @property
    def rate_limit(self) -> RateLimit:
        return RateLimit(self._data["rateLimit"])

    @property
    def vendor(self) -> Optional[str]:
        return self._data.get("vendor")
    


class OmadaWiredClient(OmadaConnectedClient):

    @property
    def dot1xVlan(self) -> int:
        """ Network name corresponding to the VLAN obtained by 802.1x D-VLAN """
        return self._data["dot1xVlan"]

    @property
    def gateway_mac(self) -> Optional[str]:
        """ Mac address of gateway the client is connected to """
        return self._data.get("switchMac")

    @property
    def gateway_name(self) -> Optional[str]:
        return self._data.get("gatewayName")

    @property
    def network_name(self) -> str:
        """ Network name """
        return self._data["networkName"]

    @property
    def port(self) -> int:
        """ Switch port client is connected to """
        return self._data["port"]

    @property
    def switch_mac(self) -> Optional[str]:
        """ Mac address of switch the client is connected to """
        return self._data.get("switchMac")

    @property
    def switch_name(self) -> Optional[str]:
        """ Name of switch the client is connected to """
        return self._data.get("switchName")

class OmadaWiredClientDetails(OmadaWiredClient, OmadaClientDetails):
    pass

class OmadaWirelessClient(OmadaConnectedClient):

    @property
    def ap_mac(self) -> str:
        """ Access point mac address """
        return self._data["apMac"]

    @property
    def ap_name(self) -> str:
        """ Access point name """
        return self._data["apName"]

    @property
    def channel(self) -> int:
        return self._data["channel"]

    @property
    def is_power_save(self) -> bool:
        """ Indicates if power save mode is enabled """
        return self._data["powerSave"]

    @property
    def radio_id(self) -> RadioId:
        """ Radio frequency id """
        return self._data["radioId"]

    @property
    def rssi(self) -> int:
        """ Signal strength in dBm """
        return self._data["rssi"]

    @property
    def rx_rate(self) -> int:
        """ Uplink negotiation rate in Kbit/s """
        return self._data["rxRate"]

    @property
    def signal_level(self) -> int:
        """ Signal strength percentage """
        return self._data["signalLevel"]

    @property
    def signal_rank(self) -> int:
        """ Signal strength (0-5) """
        return self._data["signalRank"]

    @property
    def ssid(self) -> str:
        """ SSID name """
        return self._data["ssid"]

    @property
    def tx_rate(self) -> int:
        """ Downlink negotiation rate (Kbit/s) """
        return self._data["txRate"]

    @property
    def wifi_mode(self) -> WifiMode:
        """ WiFi mode """
        return self._data["wifiMode"]

class OmadaWirelessClientDetails(OmadaWirelessClient, OmadaClientDetails):
    pass