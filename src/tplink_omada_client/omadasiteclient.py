"""Client for Omada Site requests."""

from typing import AsyncIterable, List, Optional, Union

from .clients import (
    OmadaClientDetails,
    OmadaConnectedClient,
    OmadaNetworkClient,
    OmadaWiredClient,
    OmadaWiredClientDetails,
    OmadaWirelessClient,
    OmadaWirelessClientDetails,
)
from .definitions import BandwidthControl, Eth802Dot1X, LinkDuplex, LinkSpeed, PoEMode, LedSetting
from .devices import (
    OmadaAccessPoint,
    OmadaDevice,
    OmadaFirmwareUpdate,
    OmadaGateway,
    OmadaGatewayPortConfig,
    OmadaGatewayPortStatus,
    OmadaListDevice,
    OmadaPortProfile,
    OmadaSwitch,
    OmadaSwitchPort,
    OmadaSwitchPortDetails,
    OmadaAccesPointLanPortSettings,
)
from .exceptions import (
    InvalidDevice,
)
from .omadaapiconnection import OmadaApiConnection


class SwitchPortOverrides:
    """
    Overrides that can be applied to a switch port.

    Currently, we don't support bandwidth limits and mirroring modes.
    Due to the way the API works, we have to specify overrides for everything,
    we can't just override a single profile setting. Therefore, you may need to
    initialise all of these parameters to avoid overwriting settings.
    """

    def __init__(
        self,
        enable_poe: bool = True,
        dot1x_mode: Eth802Dot1X = Eth802Dot1X.FORCE_AUTHORIZED,
        duplex: LinkDuplex = LinkDuplex.AUTO,
        link_speed: LinkSpeed = LinkSpeed.SPEED_AUTO,
        lldp_med_enable: bool = True,
        loopback_detect: bool = True,
        spanning_tree_enable: bool = False,
        port_isolation: bool = False,
    ):
        self.enable_poe = enable_poe
        self.dot1x_mode = dot1x_mode
        self.duplex = duplex
        self.link_speed = link_speed
        self.lldp_med_enable = lldp_med_enable
        self.loopback_detect = loopback_detect
        self.spanning_tree_enable = spanning_tree_enable
        self.port_isolation = port_isolation


class AccessPointPortSettings:
    """
    Settings that can be applied to network ports on access points

    Specify the values you want to modify. The remaining values will be unaffected
    """

    def __init__(
        self,
        enable_poe: Optional[bool] = None,
        vlan_enable: Optional[bool] = None,
        vlan_id: Optional[int] = None,
    ):
        self.enable_poe = enable_poe
        self.vlan_enable = vlan_enable
        self.vlan_id = vlan_id

class GatewayPortSettings:
    """
    Settings that can be applied to network ports on gateways

    Specify the values you want to modify. The remaining values will be unaffected
    """
    def __init__(
        self,
        enable_poe: Optional[bool] = None
    ):
        self.enable_poe = enable_poe

class OmadaSiteClient:
    """Client for querying an Omada site's devices."""

    def __init__(self, site_id: str, api: OmadaApiConnection):
        self._api = api
        self._site_id = site_id

    async def block_client(self, mac_or_client: Union[str, OmadaNetworkClient]) -> None:
        if isinstance(mac_or_client, OmadaConnectedClient):
            mac = mac_or_client.mac
        else:
            mac = mac_or_client
        await self._api.request(
            "post", self._api.format_url(f"cmd/clients/{mac}/block", self._site_id)
        )

    async def unblock_client(self, mac_or_client: Union[str, OmadaNetworkClient]) -> None:
        if isinstance(mac_or_client, OmadaConnectedClient):
            mac = mac_or_client.mac
        else:
            mac = mac_or_client
        await self._api.request(
            "post", self._api.format_url(f"cmd/clients/{mac}/unblock", self._site_id)
        )

    async def get_client(self, mac_or_client: Union[str, OmadaNetworkClient]) -> OmadaClientDetails:
        """Get the details of a client"""
        if isinstance(mac_or_client, OmadaConnectedClient):
            mac = mac_or_client.mac
        else:
            mac = mac_or_client

        result = await self._api.request(
            "get", self._api.format_url(f"clients/{mac}", self._site_id)
        )

        if result.get("wireless"):
            return OmadaWirelessClientDetails(result)
        else:
            return OmadaWiredClientDetails(result)

    async def get_connected_clients(self) -> AsyncIterable[OmadaConnectedClient]:
        """Get the clients connected to the site network."""
        async for client in self._api.iterate_pages(self._api.format_url("clients", self._site_id), {"filters.active": "false"}):
            if client["wireless"]:
                yield OmadaWirelessClient(client)
            else:
                yield OmadaWiredClient(client)

    async def get_known_clients(self) -> AsyncIterable[OmadaNetworkClient]:
        """Get the clients connected to the site network."""
        async for client in self._api.iterate_pages(self._api.format_url("insight/clients", self._site_id)):
            if client["wireless"]:
                yield OmadaWirelessClient(client)
            else:
                yield OmadaWiredClient(client)

    async def get_devices(self) -> List[OmadaListDevice]:
        """Get the list of devices on the site."""

        result = await self._api.request(
            "get", self._api.format_url("devices", self._site_id)
        )

        return [OmadaListDevice(d) for d in result]

    async def get_device(self, mac: str) -> OmadaListDevice:
        """ Get a single device by mac."""
        # So wasteful
        return next(d for d in await self.get_devices() if d.mac == mac)

    async def get_switches(self) -> List[OmadaSwitch]:
        """Get the list of switches on the site."""

        return [
            await self.get_switch(d)
            for d in await self.get_devices()
            if d.type == "switch"
        ]

    async def get_access_points(self) -> List[OmadaAccessPoint]:
        """Get the list of access points on the site."""

        return [
            await self.get_access_point(d)
            for d in await self.get_devices()
            if d.type == "ap"
        ]
    
    async def get_access_point(
        self, mac_or_device: Union[str, OmadaDevice]
    ) -> OmadaAccessPoint:
        """Get an access point by Mac address or Omada device."""

        if isinstance(mac_or_device, OmadaDevice):
            if mac_or_device.type != "ap":
                raise InvalidDevice()
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        result = await self._api.request(
            "get", self._api.format_url(f"eaps/{mac}", self._site_id)
        )

        return OmadaAccessPoint(result)
    
    async def get_access_point_port(
        self, mac_or_device: Union[str, OmadaDevice],
        port_name: str) -> OmadaAccesPointLanPortSettings:
        """Get the config of a single network port on an access point."""
        ap = await self.get_access_point(mac_or_device)

        port = next(p for p in ap.lan_port_settings if p.port_name == port_name)
        if(port is None):
            raise InvalidDevice(f"Port {port_name} not found")
        return port


    async def get_switch(self, mac_or_device: Union[str, OmadaDevice]) -> OmadaSwitch:
        """Get a switch by Mac address or Omada device."""

        if isinstance(mac_or_device, OmadaDevice):
            if mac_or_device.type != "switch":
                raise InvalidDevice()
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        result = await self._api.request(
            "get", self._api.format_url(f"switches/{mac}", self._site_id)
        )

        return OmadaSwitch(result)

    async def get_switch_ports(
        self, mac_or_device: Union[str, OmadaDevice]
    ) -> List[OmadaSwitchPortDetails]:
        """Get ports of a switch by Mac address or Omada device."""

        if isinstance(mac_or_device, OmadaDevice):
            if mac_or_device.type != "switch":
                raise InvalidDevice()
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        result = await self._api.request(
            "get", self._api.format_url(f"switches/{mac}/ports", self._site_id)
        )

        return [OmadaSwitchPortDetails(p) for p in result]

    async def get_switch_port(
        self,
        mac_or_device: Union[str, OmadaDevice],
        index_or_port: Union[int, OmadaSwitchPort],
    ) -> OmadaSwitchPortDetails:
        """Get a single port of a switch by Mac address or Omada device,
            and port number or port object of OmadaSwitch device."""

        if isinstance(mac_or_device, OmadaDevice):
            if mac_or_device.type != "switch":
                raise InvalidDevice()
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        if isinstance(index_or_port, OmadaSwitchPort):
            port = index_or_port.port
        else:
            port = index_or_port

        result = await self._api.request(
            "get", self._api.format_url(f"switches/{mac}/ports/{port}", self._site_id)
        )

        return OmadaSwitchPortDetails(result)

    async def get_switch_port_overrides(
        self,
        mac_or_device: Union[str, OmadaDevice],
        index_or_port: Union[int, OmadaSwitchPort],
    ) -> SwitchPortOverrides:
        """Return the current override settings for the port of a switch, or the current profile settings as default."""

        port = await self.get_switch_port(mac_or_device, index_or_port)

        # Returns the current overrides
        if port.has_profile_override:
            return SwitchPortOverrides(
                    enable_poe=(port.poe_mode == PoEMode.ENABLED),
                    dot1x_mode=port.eth_802_1x_control,
                    duplex=port.duplex,
                    link_speed=port.link_speed,
                    lldp_med_enable=port.lldp_med_enabled,
                    loopback_detect=port.loopback_detect_enabled,
                    spanning_tree_enable=port.spanning_tree_enabled,
                    port_isolation=port.port_isolation_enabled
            )

        # Otherwise the profile's config values are returned
        prof = await self.get_port_profile(port.profile_id)

        # The API doesn't provide the PoE mode of the switch (couldn't even find in Omada
        # GUI how to set the PoE mode of a switch). Thus, use True as a default value.
        poe_mode = (prof.poe_mode != PoEMode.DISABLED)

        return SwitchPortOverrides(
                enable_poe=poe_mode,
                dot1x_mode=prof.eth_802_1x_control,
                duplex=LinkDuplex.AUTO,
                link_speed=LinkSpeed.SPEED_AUTO,
                lldp_med_enable=prof.lldp_med_enabled,
                loopback_detect=prof.loopback_detect_enabled,
                spanning_tree_enable=prof.spanning_tree_enabled,
                port_isolation=prof.port_isolation_enabled
        )

    async def update_access_point_port(
        self,
        mac_or_device: Union[str, OmadaDevice],
        port_name: str,
        setting: AccessPointPortSettings,
    ) -> OmadaAccesPointLanPortSettings:
        """Update the settings for a lan port on the access point."""

        # Get the latest representation of the acccess point
        access_point = await self.get_access_point(mac_or_device)

        port_settings = [
            {
                "id": port_name,
                "lanPort": port_name,
                "localVlanEnable": setting.vlan_enable
                if setting.vlan_enable is not None
                else ps.local_vlan_enable,
                "localVlanId": setting.vlan_id
                if setting.vlan_id is not None
                else ps.local_vlan_id,
                "poeOutEnable": setting.enable_poe
                if setting.enable_poe is not None and ps.supports_poe
                else ps.poe_enable,
            }
            for ps in access_point.lan_port_settings
            if ps.port_name == port_name
        ]

        payload = {"lanPortSettings": port_settings}

        result = await self._api.request(
            "patch",
            self._api.format_url(f"eaps/{access_point.mac}", self._site_id),
            payload=payload,
        )

        updated_ap = OmadaAccessPoint(result)
        # The caller probably only cares about the updated port status
        return next(p for p in updated_ap.lan_port_settings if p.port_name == port_name)

    async def update_switch_port(
        self,
        mac_or_device: Union[str, OmadaDevice],
        index_or_port: Union[int, OmadaSwitchPort],
        new_name: Optional[str] = None,
        profile_id: Optional[str] = None,
        overrides: Optional[SwitchPortOverrides] = None,
    ) -> OmadaSwitchPortDetails:
        """Applies an existing profile to a switch on the port"""

        if isinstance(mac_or_device, OmadaDevice):
            if mac_or_device.type != "switch":
                raise InvalidDevice()
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        if isinstance(index_or_port, OmadaSwitchPort):
            port = index_or_port
        else:
            port = await self.get_switch_port(mac_or_device, index_or_port)

        payload = {
            "name": new_name or port.name,
            "profileId": profile_id or port.profile_id,
            "profileOverrideEnable": not overrides is None,
        }
        if overrides:
            payload["operation"] = "switching"
            payload["bandWidthCtrlType"] = BandwidthControl.OFF
            payload["poe"] = (
                PoEMode.ENABLED if overrides.enable_poe else PoEMode.DISABLED
            )
            payload["dot1x"] = overrides.dot1x_mode
            payload["duplex"] = overrides.duplex
            payload["linkSpeed"] = overrides.link_speed
            payload["lldpMedEnable"] = overrides.lldp_med_enable
            payload["loopbackDetectEnable"] = overrides.loopback_detect
            payload["spanningTreeEnable"] = overrides.spanning_tree_enable
            payload["portIsolationEnable"] = overrides.port_isolation
            payload["topoNotifyEnable"] = False

        await self._api.request(
            "patch",
            self._api.format_url(f"switches/{mac}/ports/{port.port}", self._site_id),
            payload=payload,
        )

        # Read back the new port settings
        return await self.get_switch_port(mac, port)

    async def get_port_profile(self, profile_id: str) -> OmadaPortProfile:
        profiles = await self.get_port_profiles()

        profile = next((p for p in profiles if p.profile_id == profile_id), None)

        if not profile:
            raise InvalidDevice(f"Port profile {profile_id} does not exist")
        return profile

    async def get_port_profiles(self) -> List[OmadaPortProfile]:
        """Lists the available switch port profiles that can be applied."""

        result = await self._api.request(
            "get", self._api.format_url("setting/lan/profileSummary", self._site_id)
        )

        return [OmadaPortProfile(p) for p in result["data"]]

    async def get_firmware_details(
        self, mac_or_device: Union[str, OmadaDevice]
    ) -> OmadaFirmwareUpdate:
        """Get details of the device firware and available upgrades."""

        if isinstance(mac_or_device, OmadaDevice):
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        result = await self._api.request(
            "get", self._api.format_url(f"devices/{mac}/firmware", self._site_id)
        )

        return OmadaFirmwareUpdate(result)

    async def start_firmware_upgrade(
        self, mac_or_device: Union[str, OmadaDevice]
    ) -> bool:
        """Begin an automatic firmware upgrade of the specified device"""

        if isinstance(mac_or_device, OmadaDevice):
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        payload = {"mac": mac}
        await self._api.request(
            "post",
            self._api.format_url(f"cmd/devices/{mac}/onlineUpgrade", self._site_id),
            payload=payload,
        )

        return True

    async def get_gateways(self) -> List[OmadaGateway]:
        """Get the list of gateways (routers) on the site. (Zero or one!)"""

        return [
            await self.get_gateway(d)
            for d in await self.get_devices()
            if d.type == "gateway"
        ]

    async def _get_gateway_mac(self, mac_or_device: Union[str, OmadaDevice, None]) -> str:
            if mac_or_device is None:
                mac_or_device = next((d for d in await self.get_devices() if d.type == "gateway"), None)
                if mac_or_device is None:
                    raise InvalidDevice("No gateways found in site")

            if isinstance(mac_or_device, OmadaDevice):
                if mac_or_device.type != "gateway":
                    raise InvalidDevice()
                return mac_or_device.mac
            else:
                return mac_or_device
            
    async def get_gateway(self, mac_or_device: Union[str, OmadaDevice, None] = None) -> OmadaGateway:
        """Get the gatway (router) for the site by Mac address or Omada device. (There can be only one!)"""

        mac = await self._get_gateway_mac(mac_or_device)
        result = await self._api.request(
            "get", self._api.format_url(f"gateways/{mac}", self._site_id)
        )

        return OmadaGateway(result)
    
    async def get_gateway_port(self, port_id: int, mac_or_deviec: Union[str, OmadaDevice, None] = None) -> OmadaGatewayPortConfig:
        """Get the port config for a specified port on the gateway"""
        gw = await self.get_gateway(mac_or_deviec)
        port_config = next(p for p in gw.port_configs if p.port_number == port_id)
        if port_config is None:
            raise InvalidDevice(f"Port {port_id} not found")
        return port_config
    
    async def set_gateway_wan_port_connect_state(self, port_id: int, connect: bool, mac_or_device: Union[str, OmadaDevice, None] = None, ipv6:bool = False) -> OmadaGatewayPortStatus:
        """Connects or disconnects the specified WAN port of the gateway to the internet."""
        mac = await self._get_gateway_mac(mac_or_device)
        payload = {"portId": port_id, "operation": 1 if connect else 0}

        result = await self._api.request(
            "post", self._api.format_url(f"cmd/gateways/{mac}/{'ipv6State' if ipv6 else 'internetState'}", self._site_id), payload=payload)
        return OmadaGatewayPortStatus(result)
    
    async def set_gateway_port_settings(self, port_id: int, settings: GatewayPortSettings, mac_or_device: Union[str, OmadaDevice, None] = None) -> OmadaGatewayPortConfig:
        """Sets the settings for the specified port of the gateway."""
        mac = await self._get_gateway_mac(mac_or_device)

        # Currently, we (and the Omada API) only supports PoE, so if the caller isn't asking for a PoE change, it's a no-op, but we should still return the current settings
        if settings.enable_poe is not None:

            # Reject requests that ask to set PoE on gateways that don't support it
            gw = await self.get_gateway(mac)
            if not gw.supports_poe and settings.enable_poe is not None:
                raise InvalidDevice("This gateway does not support PoE")

            # Thanks to dkriegner, we know the request format is:
            # {"lldpEnable":false,"echoServer":"0.0.0.0","poeSettings":[{"enable":true,"portId":5},{"enable":true,"portId":6},{"enable":true,"portId":7},{"enable":true,"portId":8},{"enable":true,"portId":9},{"enable":true,"portId":10},{"enable":true,"portId":11},{"enable":true,"portId":12}]}
            # We probably don't need to specify all of these for PATCH, but it's what the UI does, and I have no way of testing
            payload = {
                "lldpEnable": gw.lldp_enabled,
                "echoServer": gw.echo_server,
                "poeSettings": [
                    # Output an entry for every port that supports PoE, setting the appropriate port as requested
                    {
                        "enable": settings.enable_poe if settings.enable_poe is not None and port_id == p.port_number else p.poe_mode == PoEMode.ENABLED,
                        "portId": p.port_number
                    } for p in gw.port_configs if p.poe_mode != PoEMode.NONE
                ]
            }
            
            await self._api.request(
                "patch", self._api.format_url(gw.resource_path, self._site_id), payload=payload)
            
        # The result data includes an incomplete representation of the gateway port state, so we just request a new update
        return await self.get_gateway_port(port_id, mac)

    async def set_led_setting(self, mac_or_device: Union[str, OmadaDevice], setting: LedSetting) -> bool:
        """Sets the onboard LED setting for the device"""
        if isinstance(mac_or_device, OmadaDevice):
            device = mac_or_device
        else:
            device = await self.get_device(mac_or_device)

        payload = {"mac": device.mac, "ledSetting": setting.value }
        await self._api.request(
            "patch",
            self._api.format_url(device.resource_path, self._site_id),
            payload=payload,
        )

        return True

    async def set_client_name(self, mac_or_client: Union[str, OmadaNetworkClient], name):
        """Sets the name of a client"""
        if isinstance(mac_or_client, OmadaConnectedClient):
            mac = mac_or_client.mac
        else:
            mac = mac_or_client
        payload = {"name": name }
        await self._api.request(
            "patch",
            self._api.format_url(f"clients/{mac}", self._site_id),
            payload=payload,
        )

        return True


