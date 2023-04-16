""" Simple Http client for Omada controller REST api. """
from typing import NamedTuple, Optional, Union
from aiohttp.client import ClientSession

from .omadasiteclient import OmadaSiteClient
from .omadaapiconnection import OmadaApiConnection


from .exceptions import (
    SiteNotFound,
)
from .devices import (
    OmadaInterfaceDetails,
)


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
        websession: Optional[ClientSession] = None,
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

    async def get_controller_name(self) -> str:
        """Get the display name of the Omada controller."""
        result = await self._api.request(
            "get", self._api.format_url("maintenance/uiInterface")
        )

        return OmadaInterfaceDetails(result).controller_name

    async def get_sites(self) -> list[OmadaSite]:
        """Get basic list of sites the user can see"""
        response = await self._api.request("get", self._api.format_url("users/current"))

        sites = [OmadaSite(s["name"], s["key"]) for s in response["privilege"]["sites"]]
        return sites

    async def get_site_client(self, site: Union[str, OmadaSite]) -> OmadaSiteClient:
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
