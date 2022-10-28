""" Simple Http client for Omada controller REST api. """
import time
from typing import (List, Tuple, Optional, Any, Union)
from aiohttp import client_exceptions
from aiohttp.client import ClientSession

from .definitions import BandwidthControl, Eth802Dot1X, LinkDuplex, LinkSpeed, PoEMode

from .exceptions import (
    InvalidDevice,
    UnsupportedControllerVersion,
    SiteNotFound,
    RequestFailed,
    ConnectionFailed,
    BadControllerUrl
)
from .devices import (
    OmadaDevice,
    OmadaPortProfile,
    OmadaSwitch,
    OmadaSwitchPort,
    OmadaSwitchPortDetails
)

class SwitchPortOverrides:
    """
    Overrides that can be applied to a switch port.

    Currently, we don't support bandwidth limits and mirroring modes.
    Due to the way the API works, we have to specify overrides for everything,
    we can't just override a single profile setting. Therefore, you may need to
    initialise all of these parameters to avoid overwriting settings.
    """
    def __init__(self,
        enable_poe: bool = True,
        dot1x_mode: Eth802Dot1X = Eth802Dot1X.FORCE_AUTHORIZED,
        duplex: LinkDuplex = LinkDuplex.AUTO,
        link_speed: LinkSpeed = LinkSpeed.SPEED_AUTO,
        lldp_med_enable: bool = True,
        loopback_detect: bool = True,
        spanning_tree_enable: bool = False,
        port_isolation: bool = False
    ):
        self.enable_poe = enable_poe
        self.dot1x_mode = dot1x_mode
        self.duplex = duplex
        self.link_speed = link_speed
        self.lldp_med_enable = lldp_med_enable
        self.loopback_detect = loopback_detect
        self.spanning_tree_enable = spanning_tree_enable
        self.port_isolation = port_isolation


class OmadaClient:
    """
    Simple client for Omada controller API

    Provides a very limited subset of the API documented in the
    'Omada_SDN_Controller_V5.0.15 API Document'
    """

    _own_session: bool
    _controller_id: str
    _controller_version: str
    _site_id: str
    _csrf_token: Optional[str]
    _last_logon: float

    def __init__(
            self,
            url: str,
            username: str,
            password: str,
            websession: Optional[ClientSession] = None,
            site: str = "Default",
            verify_ssl=True,
    ):

        self._url = url
        self._site = site
        self._username = username
        self._password = password
        self._session = websession
        self._verify_ssl = verify_ssl
        self._csrf_token = None

    async def _get_session(self) -> ClientSession:
        if self._session is None:
            self._own_session = True
            self._session = ClientSession()
        return self._session

    async def __aenter__(self):
        await self.login()
        return self

    async def __aexit__(self, *args):
        """Call when the client is disposed."""
        # Close the web session, if we created it (i.e. it was not passed in)
        if self._own_session:
            await self.close()

    async def close(self):
        """Close the current web session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def login(self) -> None:
        """
        Call to obtain login token, controller id, and site id.

        Calls to login are optional, as the API will automatically authenticate as necessary.
        However, you may want to attempt a login to check connectivity.
        """

        version, controller_id = await self._get_controller_info()

        # Alphabetical is good enough for now
        if version < "5.0.0":
            raise UnsupportedControllerVersion(self._controller_version)

        self._controller_id = controller_id
        self._controller_version = version

        auth = {"username": self._username, "password": self._password}
        response = await self._request("post", self._format_url("login"), payload=auth)

        self._csrf_token = response["token"]
        self._last_logon = time.time()

        self._site_id = await self._get_site_id(self._site)

    async def get_devices(self) -> List[OmadaDevice]:
        """ Get the list of devices on the site. """

        result = await self._authenticated_request(
            "get",
            self._format_url("devices", self._site_id)
        )

        return [OmadaDevice(d)
            for d in result]

    async def get_switches(self) -> List[OmadaSwitch]:
        """ Get the list of switches on the site. """

        return [await self.get_switch(d) for d in await self.get_devices() if d.type == "switch"]

    async def get_switch(self, mac_or_device: Union[str, OmadaDevice]) -> OmadaSwitch:
        """ Get a switch by Mac address or Omada device. """

        if isinstance(mac_or_device, OmadaDevice):
            if mac_or_device.type != "switch":
                raise InvalidDevice()
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        result = await self._authenticated_request(
            "get",
            self._format_url(f"switches/{mac}", self._site_id)
        )

        return OmadaSwitch(result)

    async def get_switch_ports(
        self,
        mac_or_device: Union[str, OmadaDevice]
        ) -> List[OmadaSwitchPortDetails]:
        """ Get a switch by Mac address or Omada device. """

        if isinstance(mac_or_device, OmadaDevice):
            if mac_or_device.type != "switch":
                raise InvalidDevice()
            mac = mac_or_device.mac
        else:
            mac = mac_or_device

        result = await self._authenticated_request(
            "get",
            self._format_url(f"switches/{mac}/ports", self._site_id)
        )

        return [OmadaSwitchPortDetails(p) for p in result]

    async def get_switch_port(
        self,
        mac_or_device: Union[str, OmadaDevice],
        index_or_port: Union[int, OmadaSwitchPort]
        ) -> OmadaSwitchPortDetails:
        """ Get a switch by Mac address or Omada device. """

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

        result = await self._authenticated_request(
            "get",
            self._format_url(f"switches/{mac}/ports/{port}", self._site_id)
        )

        return OmadaSwitchPortDetails(result)

    async def update_switch_port(
        self,
        mac_or_device: Union[str, OmadaDevice],
        index_or_port: Union[int, OmadaSwitchPort],
        new_name: Optional[str] = None,
        profile_id: Optional[str] = None,
        overrides: Optional[SwitchPortOverrides] = None
        ) -> OmadaSwitchPortDetails:
        """ Applies an existing profile to a switch on the port """

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
            "profileOverrideEnable": not overrides is None
            }
        if overrides:
            payload["operation"] = "switching"
            payload["bandWidthCtrlType"] = BandwidthControl.OFF
            payload["poe"] = PoEMode.ENABLED if overrides.enable_poe else PoEMode.DISABLED
            payload["dot1x"] = overrides.dot1x_mode
            payload["duplex"] = overrides.duplex
            payload["linkSpeed"] = overrides.link_speed
            payload["lldpMedEnable"] = overrides.lldp_med_enable
            payload["loopbackDetectEnable"] = overrides.loopback_detect
            payload["spanningTreeEnable"] = overrides.spanning_tree_enable
            payload["portIsolationEnable"] = overrides.port_isolation
            payload["topoNotifyEnable"] = False

        await self._authenticated_request(
            "patch",
            self._format_url(f"switches/{mac}/ports/{port.port}", self._site_id),
            payload = payload
        )

        # Read back the new port settings
        return await self.get_switch_port(mac, port)

    async def get_port_profiles(self) -> List[OmadaPortProfile]:
        """ Lists the available switch port profiles that can be applied. """

        result = await self._authenticated_request(
            "get",
            self._format_url("setting/lan/profileSummary", self._site_id)
        )

        return [OmadaPortProfile(p) for p in result["data"]]

    async def _check_login(self) -> bool:
        if not self._csrf_token:
            return False

        if time.time() - self._last_logon < 60 * 60:
            # Assume 1hr is good for a login to remain active
            return True

        try:
            response = await self._request("get", self._format_url("loginStatus"))
            logged_in = bool(response["login"])
            if logged_in:
                self._last_logon = time.time()
            return logged_in
        except:
            return False

    async def _get_controller_info(self) -> Tuple[str, str]:
        """Get Omada controller version and Id (unauthenticated)."""

        response = await self._request("get", f"{self._url}/api/info")

        return (response["controllerVer"],response["omadacId"])

    async def _get_site_id(self, site_name: str):
        """Get site id by (display) name"""

        # The current user object has a list of allowed sites to administer
        response = await self._authenticated_request("get", self._format_url("users/current"))

        sites = [
            s["key"]
            for s in response["privilege"]["sites"]
            if s["name"] == site_name
        ]

        if len(sites):
            return sites[0]

        raise SiteNotFound(f"Site '{site_name}' not found")

    def _format_url(self, end_point:str, site:Optional[str]=None) -> str:
        """Get a REST url for the controller action"""

        if site:
            end_point = f"sites/{site}/{end_point}"

        return f"{self._url}/{self._controller_id}/api/v2/{end_point}"

    async def _authenticated_request(self, method: str, url: str, params=None, payload=None) -> Any:
        """Perform a request specific to the controlller"""

        if not await self._check_login():
            await self.login()

        return await self._request(method, url, params=params, payload=payload)

    async def _request(self, method: str, url: str, params=None, payload=None) -> Any:
        """Perform a request on the controller, and unpack the response."""

        session = await self._get_session()

        # Note: Auth happens via cookies, set during the login command, but we also get a CSRF token
        # which we need to push back
        headers = {}
        if self._csrf_token:
            headers["Csrf-Token"] = self._csrf_token

        try:
            async with session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    json=payload,
                    ssl=self._verify_ssl,
            ) as response:

                if response.status != 200:
                    if response.content_type == "application/json":
                        content = await response.json()
                        self._check_application_errors(content)

                    raise RequestFailed(response.status, "HTTP Request Error")

                content = await response.json()
                self._check_application_errors(content)

                # Unpack response data
                if "result" in content:
                    return content["result"]
                return content

        except client_exceptions.InvalidURL as err:
            raise BadControllerUrl(err) from err
        except client_exceptions.ClientConnectionError as err:
            raise ConnectionFailed(err) from err
        except client_exceptions.ClientError as err:
            raise RequestFailed(0, f"Unexpected error: {err}") from None

    def _check_application_errors(self, response):
        if not isinstance(response, dict):
            return
        if response["errorCode"] == 0:
            return

        raise RequestFailed(response["errorCode"], response["msg"])
