"""Client for Omada Site requests."""

from typing import List, Optional, Union
from .omadaapiconnection import OmadaApiConnection

from .devices import (
    OmadaAccessPoint,
    OmadaDevice,
    OmadaFirmwareUpdate,
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

from .definitions import BandwidthControl, Eth802Dot1X, LinkDuplex, LinkSpeed, PoEMode


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


class OmadaSiteClient:
    """Client for querying an Omada site's devices."""

    def __init__(self, site_id: str, api: OmadaApiConnection):
        self._api = api
        self._site_id = site_id

    async def get_devices(self) -> List[OmadaListDevice]:
        """Get the list of devices on the site."""

        result = await self._api.request(
            "get", self._api.format_url("devices", self._site_id)
        )

        return [OmadaListDevice(d) for d in result]

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
        """Get a switch by Mac address or Omada device."""

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
        """Get a switch by Mac address or Omada device."""

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
