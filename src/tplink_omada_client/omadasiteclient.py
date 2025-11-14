"""Client for Omada Site requests."""

from typing import AsyncIterable
from dataclasses import dataclass

from awesomeversion import AwesomeVersion

from .clients import (
    OmadaClientDetails,
    OmadaConnectedClient,
    OmadaNetworkClient,
    OmadaWiredClient,
    OmadaWiredClientDetails,
    OmadaWirelessClient,
    OmadaWirelessClientDetails,
)
from .definitions import (
    BandwidthControl,
    Eth802Dot1X,
    LinkDuplex,
    LinkSpeed,
    NetworkTagsSetting,
    PoEMode,
    LedSetting,
)
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


@dataclass
class PortProfileOverrides:
    """
    Overrides that can be applied to a switch port.
    Leaving these as None should leave the existing setting unchanged.

    Currently, we don't support bandwidth limits and mirroring modes, these WILL get reset regardless
    """

    enable_poe: bool | None = None
    dot1x_mode: Eth802Dot1X | None = None
    lldp_med_enable: bool | None = None
    loopback_detect: bool | None = None
    spanning_tree_enable: bool | None = None
    port_isolation: bool | None = None
    loopback_detect_vlan_based: bool | None = None
    flow_control: bool | None = None
    eee: bool | None = None


@dataclass
class SwitchPortSettings:
    """
    Settings that can be applied to a switch port

    Specify the values you want to modify. The remaining values will be unaffected
    """

    name: str | None = None
    # Port profile to apply
    profile_id: str | None = None
    native_network_id: str | None = None
    duplex: LinkDuplex | None = None
    link_speed: LinkSpeed | None = None
    # Port labels
    tag_ids: list[str] | None = None
    network_tags_setting: NetworkTagsSetting | None = None
    # Set if network_tags_setting is CUSTOM
    tagged_network_ids: list[str] | None = None
    untagged_network_ids: list[str] | None = None
    # Voice network
    voice_network: bool | None = None
    # Set if voice_network is True
    voice_network_id: str | None = None

    profile_override_enabled: bool | None = None
    # Set if profile_override_enabled is True to specify overrides, otherwise the profile's settings are used
    profile_overrides: PortProfileOverrides | None = None


@dataclass
class AccessPointPortSettings:
    """
    Settings that can be applied to network ports on access points

    Specify the values you want to modify. The remaining values will be unaffected
    """

    enable_poe: bool | None = None
    vlan_enable: bool | None = None
    vlan_id: int | None = None


@dataclass
class GatewayPortSettings:
    """
    Settings that can be applied to network ports on gateways

    Specify the values you want to modify. The remaining values will be unaffected
    """

    enable_poe: bool | None = None


@dataclass
class OmadaClientFixedAddress:
    """
    Describes a fixed IP address reservation for a client
    """

    network_id: str | None = None
    ip_address: str | None = None


@dataclass
class OmadaClientSettings:
    """
    Settings that can be applied to a client
    """

    name: str | None = None
    lock_to_aps: list[str] | None = None
    fixed_address: OmadaClientFixedAddress | None = None


class OmadaSiteClient:
    """Client for querying an Omada site's devices."""

    def __init__(self, site_id: str, api: OmadaApiConnection):
        self._api = api
        self._site_id = site_id

    async def block_client(self, mac_or_client: str | OmadaNetworkClient) -> None:
        """Block the specified client from the network."""
        if isinstance(mac_or_client, OmadaConnectedClient):
            mac = mac_or_client.mac
        else:
            mac = mac_or_client
        await self._api.request("post", self._api.format_url(f"cmd/clients/{mac}/block", self._site_id))

    async def unblock_client(self, mac_or_client: str | OmadaNetworkClient) -> None:
        """Unblock the specified client from the network."""
        if isinstance(mac_or_client, OmadaConnectedClient):
            mac = mac_or_client.mac
        else:
            mac = mac_or_client
        await self._api.request("post", self._api.format_url(f"cmd/clients/{mac}/unblock", self._site_id))

    async def reconnect_client(self, mac_or_client: str | OmadaNetworkClient) -> None:
        """Reconnect the specified client."""
        if isinstance(mac_or_client, OmadaConnectedClient):
            mac = mac_or_client.mac
        else:
            mac = mac_or_client
        await self._api.request("post", self._api.format_url(f"cmd/clients/{mac}/reconnect", self._site_id))

    async def get_client(self, mac_or_client: str | OmadaNetworkClient) -> OmadaClientDetails:
        """Get the details of a client"""
        if isinstance(mac_or_client, OmadaConnectedClient):
            mac = mac_or_client.mac
        else:
            mac = mac_or_client

        result = await self._api.request("get", self._api.format_url(f"clients/{mac}", self._site_id))

        if result.get("wireless"):
            return OmadaWirelessClientDetails(result)
        else:
            return OmadaWiredClientDetails(result)

    async def update_client(self, mac_or_client: str | OmadaNetworkClient, settings: OmadaClientSettings):
        """Update configuration of a client"""
        if isinstance(mac_or_client, OmadaConnectedClient):
            mac = mac_or_client.mac
        else:
            mac = mac_or_client

        payload = {}
        if settings.name:
            payload["name"] = settings.name
        if settings.lock_to_aps is not None:
            payload["clientLockToApSetting"] = {
                "enable": len(settings.lock_to_aps) > 0,
                "aps": settings.lock_to_aps,
            }
        if settings.fixed_address:
            if settings.fixed_address.ip_address:
                payload["ipSetting"] = {
                    "useFixedAddr": True,
                    "netId": settings.fixed_address.network_id,
                    "ip": settings.fixed_address.ip_address,
                }
            else:
                payload["ipSetting"] = {"useFixedAddr": False}
        if not payload:
            return await self.get_client(mac_or_client)

        result = await self._api.request("patch", self._api.format_url(f"clients/{mac}", self._site_id), json=payload)
        if result.get("wireless"):
            return OmadaWirelessClientDetails(result)
        else:
            return OmadaWiredClientDetails(result)

    async def get_connected_clients(self) -> AsyncIterable[OmadaConnectedClient]:
        """Get the clients connected to the site network."""
        async for client in self._api.iterate_pages(
            self._api.format_url("clients", self._site_id), {"filters.active": "false"}
        ):
            is_wireless = client.get("wireless")
            if is_wireless:
                yield OmadaWirelessClient(client)
            elif is_wireless is False:
                yield OmadaWiredClient(client)

    async def get_known_clients(self) -> AsyncIterable[OmadaNetworkClient]:
        """Get the clients connected to the site network."""
        async for client in self._api.iterate_pages(self._api.format_url("insight/clients", self._site_id)):
            is_wireless = client.get("wireless")
            if is_wireless:
                yield OmadaWirelessClient(client)
            elif is_wireless is False:
                yield OmadaWiredClient(client)

    async def get_devices(self) -> list[OmadaListDevice]:
        """Get the list of devices on the site."""

        result = await self._api.request("get", self._api.format_url("devices", self._site_id))

        return [OmadaListDevice(d) for d in result]

    async def get_device(self, mac: str) -> OmadaListDevice:
        """Get a single device by mac."""
        # So wasteful
        return next(d for d in await self.get_devices() if d.mac == mac)

    async def get_switches(self) -> list[OmadaSwitch]:
        """Get the list of switches on the site."""

        return [await self.get_switch(d) for d in await self.get_devices() if d.type == "switch"]

    async def get_access_points(self) -> list[OmadaAccessPoint]:
        """Get the list of access points on the site."""

        return [await self.get_access_point(d) for d in await self.get_devices() if d.type == "ap"]

    async def get_access_point(self, mac_or_device: str | OmadaDevice) -> OmadaAccessPoint:
        """Get an access point by Mac address or Omada device."""

        if isinstance(mac_or_device, OmadaDevice):
            if mac_or_device.type != "ap":
                raise InvalidDevice()
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        result = await self._api.request("get", self._api.format_url(f"eaps/{mac}", self._site_id))

        return OmadaAccessPoint(result)

    async def get_access_point_port(self, mac_or_device: str | OmadaDevice, port_name: str) -> OmadaAccesPointLanPortSettings:
        """Get the config of a single network port on an access point."""
        ap = await self.get_access_point(mac_or_device)

        port = next(p for p in ap.lan_port_settings if p.port_name == port_name)
        if port is None:
            raise InvalidDevice(f"Port {port_name} not found")
        return port

    async def get_switch(self, mac_or_device: str | OmadaDevice) -> OmadaSwitch:
        """Get a switch by Mac address or Omada device."""

        if isinstance(mac_or_device, OmadaDevice):
            if mac_or_device.type != "switch":
                raise InvalidDevice()
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        result = await self._api.request("get", self._api.format_url(f"switches/{mac}", self._site_id))

        return OmadaSwitch(result)

    async def get_switch_ports(self, mac_or_device: str | OmadaDevice) -> list[OmadaSwitchPortDetails]:
        """Get ports of a switch by Mac address or Omada device."""

        if isinstance(mac_or_device, OmadaDevice):
            if mac_or_device.type != "switch":
                raise InvalidDevice()
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        result = await self._api.request("get", self._api.format_url(f"switches/{mac}/ports", self._site_id))

        return [OmadaSwitchPortDetails(p) for p in result]

    async def get_switch_port(
        self,
        mac_or_device: str | OmadaDevice,
        index_or_port: int | OmadaSwitchPort,
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

        result = await self._api.request("get", self._api.format_url(f"switches/{mac}/ports/{port}", self._site_id))

        return OmadaSwitchPortDetails(result)

    async def get_switch_port_overrides(
        self,
        mac_or_device: str | OmadaDevice,
        index_or_port: int | OmadaSwitchPort,
    ) -> PortProfileOverrides:
        """Return the current override settings for the port of a switch, or the current profile settings as default."""

        port = await self.get_switch_port(mac_or_device, index_or_port)

        result = PortProfileOverrides()

        # Return the current settings based on the overrides if they exist
        if port.has_profile_override:
            result.enable_poe = port.poe_mode == PoEMode.ENABLED
            result.dot1x_mode = port.eth_802_1x_control
            result.lldp_med_enable = port.lldp_med_enabled
            result.loopback_detect = port.loopback_detect_enabled
            result.spanning_tree_enable = port.spanning_tree_enabled
            result.port_isolation = port.port_isolation_enabled
            if port.has_eee:
                result.eee = port.eee_enabled
            if port.has_flow_control:
                result.flow_control = port.flow_control_enabled
            if port.has_loopback_detect_vlan_based:
                result.loopback_detect_vlan_based = port.loopback_detect_vlan_based_enabled

            return result

        # Otherwise the profile's config values are used to augment the port settings
        prof = await self.get_port_profile(port.profile_id)

        poe_mode = prof.poe_mode != PoEMode.DISABLED

        result.enable_poe = poe_mode
        result.dot1x_mode = prof.eth_802_1x_control
        result.lldp_med_enable = prof.lldp_med_enabled
        result.loopback_detect = prof.loopback_detect_enabled
        result.spanning_tree_enable = prof.spanning_tree_enabled
        result.port_isolation = prof.port_isolation_enabled
        if prof.has_eee:
            result.eee = prof.eee_enabled
        if prof.has_flow_control:
            result.flow_control = prof.flow_control_enabled
        if prof.has_loopback_detect_vlan_based:
            result.loopback_detect_vlan_based = prof.loopback_detect_vlan_based_enabled

        return result

    async def update_access_point_port(
        self,
        mac_or_device: str | OmadaDevice,
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
                "localVlanEnable": setting.vlan_enable if setting.vlan_enable is not None else ps.local_vlan_enable,
                "localVlanId": setting.vlan_id if setting.vlan_id is not None else ps.local_vlan_id,
                "poeOutEnable": setting.enable_poe if setting.enable_poe is not None and ps.supports_poe else ps.poe_enable,
            }
            for ps in access_point.lan_port_settings
            if ps.port_name == port_name
        ]

        payload = {"lanPortSettings": port_settings}

        result = await self._api.request(
            "patch",
            self._api.format_url(f"eaps/{access_point.mac}", self._site_id),
            json=payload,
        )

        updated_ap = OmadaAccessPoint(result)
        # The caller probably only cares about the updated port status
        return next(p for p in updated_ap.lan_port_settings if p.port_name == port_name)

    async def update_switch_port(
        self,
        mac_or_device: str | OmadaDevice,
        index_or_port: int | OmadaSwitchPort,
        settings: SwitchPortSettings,
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

        override_setting = (
            settings.profile_override_enabled if settings.profile_override_enabled is not None else port.has_profile_override
        )
        payload = {
            "name": settings.name or port.name,
            "profileId": settings.profile_id or port.profile_id,
            "linkSpeed": settings.link_speed if settings.link_speed is not None else port.link_speed,
            "duplex": settings.duplex if settings.duplex is not None else port.duplex,
            "profileOverrideEnable": override_setting,
            "tagIds": settings.tag_ids if settings.tag_ids is not None else port.tag_ids,
        }

        if settings.native_network_id or port.native_network_id:
            payload["nativeNetworkId"] = settings.native_network_id or port.native_network_id

        network_tags_setting = (
            settings.network_tags_setting if settings.network_tags_setting is not None else port.network_tags_setting
        )
        if network_tags_setting != NetworkTagsSetting.UNKNOWN:
            payload["networkTagsSetting"] = network_tags_setting
            if network_tags_setting == NetworkTagsSetting.CUSTOM:
                payload["tagNetworkIds"] = (
                    settings.tagged_network_ids if settings.tagged_network_ids is not None else port.tagged_network_ids
                )
                payload["untagNetworkIds"] = (
                    settings.untagged_network_ids if settings.untagged_network_ids is not None else port.untagged_network_ids
                )

        if port.has_voice_network:
            voice_network_setting = (
                settings.voice_network if settings.voice_network is not None else port.voice_network_enabled
            )
            payload["voiceNetworkEnable"] = voice_network_setting
            if voice_network_setting:
                payload["voiceNetworkId"] = (
                    settings.voice_network_id if settings.voice_network_id is not None else port.voice_network_id
                )

        if override_setting:
            existing_overrides = await self.get_switch_port_overrides(mac, port)
            new_overrides = settings.profile_overrides or PortProfileOverrides()

            # Hacks
            payload["operation"] = "switching"
            payload["bandWidthCtrlType"] = BandwidthControl.OFF

            enable_poe = new_overrides.enable_poe if new_overrides.enable_poe is not None else existing_overrides.enable_poe
            payload["poe"] = PoEMode.ENABLED if enable_poe else PoEMode.DISABLED
            payload["dot1x"] = (
                new_overrides.dot1x_mode if new_overrides.dot1x_mode is not None else existing_overrides.dot1x_mode
            )
            payload["lldpMedEnable"] = (
                new_overrides.lldp_med_enable
                if new_overrides.lldp_med_enable is not None
                else existing_overrides.lldp_med_enable
            )
            payload["loopbackDetectEnable"] = (
                new_overrides.loopback_detect
                if new_overrides.loopback_detect is not None
                else existing_overrides.loopback_detect
            )
            payload["spanningTreeEnable"] = (
                new_overrides.spanning_tree_enable
                if new_overrides.spanning_tree_enable is not None
                else existing_overrides.spanning_tree_enable
            )
            payload["portIsolationEnable"] = (
                new_overrides.port_isolation if new_overrides.port_isolation is not None else existing_overrides.port_isolation
            )
            if (await self._api.get_controller_version()) < AwesomeVersion("6"):
                # Possibly no longer valid
                payload["topoNotifyEnable"] = False
            else:
                # Settings that might be non-optional in 6.0+ versions
                eee = new_overrides.eee if new_overrides.eee is not None else existing_overrides.eee
                if eee is not None:
                    payload["eeeEnable"] = eee
                fce = new_overrides.flow_control if new_overrides.flow_control is not None else existing_overrides.flow_control
                if fce is not None:
                    payload["flowControlEnable"] = fce
                ldvbe = (
                    new_overrides.loopback_detect_vlan_based
                    if new_overrides.loopback_detect_vlan_based is not None
                    else existing_overrides.loopback_detect_vlan_based
                )
                if ldvbe is not None:
                    payload["loopbackDetectVlanBasedEnable"] = ldvbe

                payload["dhcpL2RelaySettings"] = {"enable": False}

        if (await self._api.get_controller_version()) < AwesomeVersion("6"):
            request_url = self._api.format_url(f"switches/{mac}/ports/{port.port}", self._site_id)
        else:
            # New OpenAPI endpoint from 6.0+
            request_url = self._api.format_openapi_url(f"switches/{mac}/ports/{port.port}", self._site_id)

        await self._api.request(
            "patch",
            request_url,
            json=payload,
        )

        # Read back the new port settings
        return await self.get_switch_port(mac, port)

    async def get_port_profile(self, profile_id: str) -> OmadaPortProfile:
        """Get the details of a port profile by ID."""
        profiles = await self.get_port_profiles()

        profile = next((p for p in profiles if p.profile_id == profile_id), None)

        if not profile:
            raise InvalidDevice(f"Port profile {profile_id} does not exist")
        return profile

    async def get_port_profiles(self) -> list[OmadaPortProfile]:
        """Lists the available switch port profiles that can be applied."""

        result = await self._api.request("get", self._api.format_url("setting/lan/profileSummary", self._site_id))

        return [OmadaPortProfile(p) for p in result["data"]]

    async def get_firmware_details(self, mac_or_device: str | OmadaDevice) -> OmadaFirmwareUpdate:
        """Get details of the device firware and available upgrades."""

        if isinstance(mac_or_device, OmadaDevice):
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        result = await self._api.request("get", self._api.format_url(f"devices/{mac}/firmware", self._site_id))

        return OmadaFirmwareUpdate(result)

    async def start_firmware_upgrade(self, mac_or_device: str | OmadaDevice) -> bool:
        """Begin an automatic firmware upgrade of the specified device"""

        if isinstance(mac_or_device, OmadaDevice):
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        payload = {"mac": mac}
        await self._api.request(
            "post",
            self._api.format_url(f"cmd/devices/{mac}/onlineUpgrade", self._site_id),
            json=payload,
        )

        return True

    async def get_gateways(self) -> list[OmadaGateway]:
        """Get the list of gateways (routers) on the site. (Zero or one!)"""

        return [await self.get_gateway(d) for d in await self.get_devices() if d.type == "gateway"]

    async def _get_gateway_mac(self, mac_or_device: str | OmadaDevice | None) -> str:
        if mac_or_device is None:
            mac_or_device = next((d for d in await self.get_devices() if d.type == "gateway"), None)
            if mac_or_device is None:
                raise InvalidDevice("No gateways found in site")

        if isinstance(mac_or_device, OmadaDevice):
            if mac_or_device.type != "gateway":
                raise InvalidDevice()
            return mac_or_device.mac
        return mac_or_device

    async def get_gateway(self, mac_or_device: str | OmadaDevice | None = None) -> OmadaGateway:
        """Get the gatway (router) for the site by Mac address or Omada device. (There can be only one!)"""

        mac = await self._get_gateway_mac(mac_or_device)
        result = await self._api.request("get", self._api.format_url(f"gateways/{mac}", self._site_id))

        return OmadaGateway(result)

    async def get_gateway_port(self, port_id: int, mac_or_deviec: str | OmadaDevice | None = None) -> OmadaGatewayPortConfig:
        """Get the port config for a specified port on the gateway"""
        gw = await self.get_gateway(mac_or_deviec)
        port_config = next(p for p in gw.port_configs if p.port_number == port_id)
        if port_config is None:
            raise InvalidDevice(f"Port {port_id} not found")
        return port_config

    async def set_gateway_wan_port_connect_state(
        self,
        port_id: int,
        connect: bool,
        mac_or_device: str | OmadaDevice | None = None,
        ipv6: bool = False,
    ) -> OmadaGatewayPortStatus:
        """Connects or disconnects the specified WAN port of the gateway to the internet."""
        mac = await self._get_gateway_mac(mac_or_device)
        payload = {"portId": port_id, "operation": 1 if connect else 0}

        result = await self._api.request(
            "post",
            self._api.format_url(
                f"cmd/gateways/{mac}/{'ipv6State' if ipv6 else 'internetState'}",
                self._site_id,
            ),
            json=payload,
        )
        return OmadaGatewayPortStatus(result)

    async def set_gateway_port_settings(
        self,
        port_id: int,
        settings: GatewayPortSettings,
        mac_or_device: str | OmadaDevice | None = None,
    ) -> OmadaGatewayPortConfig:
        """Sets the settings for the specified port of the gateway."""
        mac = await self._get_gateway_mac(mac_or_device)

        # Currently, we (and the Omada API) only supports PoE, so if the caller isn't asking for a PoE change,
        # it's a no-op, but we should still return the current settings
        if settings.enable_poe is not None:
            # Reject requests that ask to set PoE on gateways that don't support it
            gw = await self.get_gateway(mac)
            if not gw.supports_poe and settings.enable_poe is not None:
                raise InvalidDevice("This gateway does not support PoE")

            # Thanks to dkriegner, we know the request format is:
            # {
            #     "lldpEnable": false,
            #     "echoServer": "0.0.0.0",
            #     "poeSettings": [
            #         {"enable": true, "portId": 5},
            #         {"enable": true, "portId": 6},
            #         {"enable": true, "portId": 7},
            #         {"enable": true, "portId": 8},
            #         {"enable": true, "portId": 9},
            #         {"enable": true, "portId": 10},
            #         {"enable": true, "portId": 11},
            #         {"enable": true, "portId": 12},
            #     ],
            # }
            # We probably don't need to specify all of these for PATCH, but it's what the UI does,
            # and I have no way of testing
            payload = {
                "lldpEnable": gw.lldp_enabled,
                "echoServer": gw.echo_server,
                "poeSettings": [
                    # Output an entry for every port that supports PoE, setting the appropriate port as requested
                    {
                        "enable": settings.enable_poe
                        if settings.enable_poe is not None and port_id == p.port_number
                        else p.poe_mode == PoEMode.ENABLED,
                        "portId": p.port_number,
                    }
                    for p in gw.port_configs
                    if p.poe_mode != PoEMode.NONE
                ],
            }

            await self._api.request(
                "patch",
                self._api.format_url(gw.resource_path, self._site_id),
                json=payload,
            )

        # The result data includes an incomplete representation of the gateway port state,
        # so we just request a new update
        return await self.get_gateway_port(port_id, mac)

    async def set_led_setting(self, mac_or_device: str | OmadaDevice, setting: LedSetting) -> bool:
        """Sets the onboard LED setting for the device"""
        if isinstance(mac_or_device, OmadaDevice):
            device = mac_or_device
        else:
            device = await self.get_device(mac_or_device)

        payload = {"mac": device.mac, "ledSetting": setting.value}
        await self._api.request(
            "patch",
            self._api.format_url(device.resource_path, self._site_id),
            json=payload,
        )

        return True
