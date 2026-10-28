"""Simple Http client for Omada controller REST api."""

import asyncio
import os
from typing import NamedTuple

from aiohttp import MultipartWriter
from aiohttp.client import ClientSession
from awesomeversion import AwesomeVersion
from multidict import CIMultiDict

from .definitions import (
    OmadaControllerInfo,
    OmadaControllerStatus,
    OmadaControllerType,
    OmadaControllerUpdateInfo,
    OmadaHardwareUpgradeStatus,
)
from .devices import (
    OmadaInterfaceDetails,
)
from .exceptions import (
    SiteNotFound,
)
from .omadaapiconnection import OmadaApiConnection
from .omadasiteclient import OmadaSiteClient


class OmadaSite(NamedTuple):
    """Identifies a site controlled by the controller."""

    name: str
    id: str


class OmadaClient:
    """
    Simple client for Omada controller API

    Provides a very limited subset of the API documented in the
    'Omada_SDN_Controller_V5.0.15 API Document'
    """

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        websession: ClientSession | None = None,
        verify_ssl=True,
    ):
        self._api = OmadaApiConnection(url, username, password, websession, verify_ssl)

    async def __aenter__(self):
        await self._api.__aenter__()
        return self

    async def __aexit__(self, *args) -> bool:
        """Call when the client is disposed."""
        # Close the web session, if we created it (i.e. it was not passed in)
        return await self._api.__aexit__(*args)

    async def login(self) -> str:
        """
        Log in to the controller and returns the controller's unique ID.

        Calls to login are optional, as the API will automatically authenticate as necessary.
        However, you may want to attempt a login to check connectivity.
        """
        return await self._api.login()

    async def get_controller_version(self) -> AwesomeVersion:
        """Get the controller version as an AwesomeVersion object."""
        return await self._api.get_controller_version()

    async def get_controller_info(self) -> OmadaControllerInfo:
        """Get diagnostic information from the Omada Controller /api/info endpoint."""
        return await self._api.get_controller_info()

    async def get_controller_name(self) -> str:
        """Get the display name of the Omada controller."""
        result = await self._api.request("get", self._api.format_url("maintenance/uiInterface"))

        return OmadaInterfaceDetails(result).controller_name

    async def get_controller_type(self) -> OmadaControllerType:
        """Get the Omada controller type."""
        result = await self._api.request("get", self._api.format_url("anon/controllerType"))

        return OmadaControllerType(result)

    async def get_controller_status(self) -> OmadaControllerStatus:
        """Get status information for the Omada controller."""
        result = await self._api.request(
            "get", self._api.format_url("maintenance/controllerStatus")
        )

        return OmadaControllerStatus(result)

    async def get_sites(self) -> list[OmadaSite]:
        """Get basic list of sites the user can see"""
        response = await self._api.request("get", self._api.format_url("users/current"))

        sites = [OmadaSite(s["name"], s["key"]) for s in response["privilege"]["sites"]]
        return sites

    async def get_site_client(self, site: str | OmadaSite) -> OmadaSiteClient:
        """Get a client that can query the specified Omada site."""
        if isinstance(site, OmadaSite):
            site_id = site.id
        else:
            site_id = await self._get_site_id(site)
        return OmadaSiteClient(site_id, self._api)

    async def _get_site_id(self, site_name: str):
        """Get site id by (display) name"""

        # The current user object has a list of allowed sites to administer
        sites = await self.get_sites()

        site_id = next((s.id for s in sites if s.name == site_name), None)

        if site_id:
            return site_id

        raise SiteNotFound(f"Site '{site_name}' not found")

    async def reboot(self) -> int:
        """
        Reboot the Omada controller.

        Returns the estimated number of seconds until the reboot finishes.
        """
        url = self._api.format_url("cmd/reboot")
        result = await self._api.request("post", url)

        return result["rebootTime"]

    async def set_certificate(self, file: str, cert_password: str):
        """Upload a new PKCS12 PFX certificate to the controller."""

        base_name = os.path.basename(file)
        cert_data = await asyncio.to_thread(_read_binary_file, file)

        with MultipartWriter("form-data") as mpwriter:
            file_part = mpwriter.append(cert_data, CIMultiDict({"Content-Type": "application/x-pkcs12"}))
            file_part.set_content_disposition("form-data", name="file", filename=base_name)

            data_part = mpwriter.append_json({"cerName": base_name})
            data_part.set_content_disposition("form-data", name="data")

            url = self._api.format_url("files/controller/certificate")
            upload_result = await self._api.request("post", url, data=mpwriter)
        cert_id = upload_result["cerId"]
        cert_name = upload_result["cerName"]

        payload = {
            "certificate": {
                "cerId": cert_id,
                "cerName": cert_name,
                "cerType": "PFX",
                "enable": True,
                "keyPassword": cert_password,
            }
        }
        url = self._api.format_url("controller/setting")
        await self._api.request("patch", url, json=payload)

    async def check_firmware_updates(self, *, channel: int | None = None) -> OmadaControllerUpdateInfo:
        """Check for controller updates, optionally selecting a release channel on 6.3+.

        By default, use the controller's configured channel. Passing a channel ID
        (0 for the release channel) only changes this check, not the controller's
        configuration. Hardware results contain firmware versions, which differ
        from the controller application version.
        """
        if await self.get_controller_version() < AwesomeVersion("6.3"):
            if channel is not None:
                raise ValueError("Release channel selection requires Omada 6.3 or later")
            result = await self._api.request("get", self._api.format_url("controller/notification/updateInfo"))
            return OmadaControllerUpdateInfo(result)

        is_hardware = not (await self.get_controller_type()).is_soft_controller
        return await self._get_channel_update_info(is_hardware, channel)

    async def _get_channel_update_info(self, is_hardware: bool, channel_id: int | None) -> OmadaControllerUpdateInfo:
        """Normalize release-channel updates for software and hardware controllers."""
        result = await self._api.request("get", self._api.format_url("maintenance/software/channelUpdate"))
        selected_channel = result.get("currentChannel") if channel_id is None else channel_id
        channel = next((entry for entry in result.get("upgradeList", []) if entry["channel"] == selected_channel), None)
        if channel is None:
            if channel_id is not None:
                raise ValueError(f"Controller did not report release channel {channel_id}")
            return OmadaControllerUpdateInfo({})

        current_version = result.get("currentControllerVer")
        if is_hardware:
            firmware = await self._api.request("get", self._api.format_url("maintenance/hardware/checkFirmware"))
            # Channel versions on hardware are firmware versions, not currentControllerVer.
            current_version = firmware.get("currentVersion")

        section = "hardware" if is_hardware else "software"
        return OmadaControllerUpdateInfo({section: {
            "upgrade": channel["update"],
            "currentVersion": current_version,
            "latestVersion": channel.get("latestVersion", current_version) if channel["update"] else current_version,
            "releaseLog": channel.get("releaseLog"),
            "releaseUrl": channel.get("releaseUrl"),
            "downloadLink": channel.get("downloadUrl"),
            "denyUpgrade": channel.get("denyUpgrade"),
        }})

    async def install_controller_firmware(self, target_version: str) -> bool:
        """Install controller firmware remotely when supported."""
        url = self._api.format_url("cmd/upgradeFirmware")
        payload = {"targetVersion": target_version}
        await self._api.request("post", url, json=payload)
        return True

    async def upgrade_controller_firmware(self, target_version: str) -> bool:
        """Upgrade the Omada hardware controller firmware to the specified version."""
        return await self.install_controller_firmware(target_version)

    async def get_controller_upgrade_status(self) -> OmadaHardwareUpgradeStatus:
        """Get the status of an ongoing hardware controller firmware upgrade."""
        url = self._api.format_url("maintenance/hardware/upgradeStatus")
        result = await self._api.request("get", url)
        return OmadaHardwareUpgradeStatus(result)


def _read_binary_file(file: str) -> bytes:
    with open(file, "rb") as upload_file:
        return upload_file.read()
