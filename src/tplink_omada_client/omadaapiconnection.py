"""Internal Omada API client."""

import time
from typing import Any, AsyncIterable, Optional, Tuple

import re
from urllib.parse import urlsplit, urljoin
from aiohttp import client_exceptions, CookieJar
from aiohttp.client import ClientSession
from awesomeversion  import AwesomeVersion

from .exceptions import (
    BadControllerUrl,
    ConnectionFailed,
    LoginFailed,
    LoginSessionClosed,
    RequestFailed,
    UnsupportedControllerVersion,
)


_PAGE_SIZE: int = 100

class OmadaApiConnection:
    """Low level Omada API client."""

    _own_session: bool
    _controller_id: str
    _controller_version: str
    _csrf_token: Optional[str]
    _last_logon: float

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        websession: Optional[ClientSession] = None,
        verify_ssl=True,
    ):

        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        url_parts = urlsplit(url, "https://")
        self._url = url_parts.geturl()
        self._host = url_parts.hostname or ""

        self._url = url
        self._username = username
        self._password = password
        self._session = websession
        self._verify_ssl = verify_ssl
        self._csrf_token = None

    async def _get_session(self) -> ClientSession:
        if self._session is None:
            self._own_session = True
            jar = (
                None
                if re.fullmatch(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", self._host)
                is None
                else CookieJar(unsafe=True)
            )
            self._session = ClientSession(cookie_jar=jar)
        return self._session

    async def __aenter__(self):
        try:
            await self.login()
            return self
        except Exception as error:
            if self._own_session:
                await self.close()
            raise error

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Call when the client is disposed."""
        # Close the web session, if we created it (i.e. it was not passed in)
        if self._own_session:
            await self.close()
        return False

    async def close(self):
        """Close the current web session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def login(self) -> str:
        """
        Call to obtain login token, controller id, and site id.

        Calls to login are optional, as the API will automatically authenticate as necessary.
        However, you may want to attempt a login to check connectivity.
        """

        version, controller_id = await self._get_controller_info()

        if AwesomeVersion(version) < AwesomeVersion("5.1.0"):
            raise UnsupportedControllerVersion(self._controller_version)

        self._controller_id = controller_id
        self._controller_version = version

        auth = {"username": self._username, "password": self._password}
        response = await self._do_request(
            "post", self.format_url("login"), payload=auth
        )

        self._csrf_token = response["token"]
        self._last_logon = time.time()

        return self._controller_id

    async def _check_login(self) -> bool:
        if not self._csrf_token:
            return False

        if time.time() - self._last_logon < 60 * 60:
            # Assume 1hr is good for a login to remain active
            return True

        try:
            response = await self._do_request("get", self.format_url("loginStatus"))
            logged_in = bool(response["login"])
            if logged_in:
                self._last_logon = time.time()
            return logged_in
        except:  # pylint: disable=bare-except
            return False

    async def _get_controller_info(self) -> Tuple[str, str]:
        """Get Omada controller version and Id (unauthenticated)."""

        response = await self._do_request("get", urljoin(self._url, "/api/info"))

        return (response["controllerVer"], response["omadacId"])

    def format_url(self, end_point: str, site: Optional[str] = None) -> str:
        """Get a REST url for the controller action"""

        if site:
            end_point = f"sites/{site}/{end_point}"

        return urljoin(self._url, f"/{self._controller_id}/api/v2/{end_point}")

    async def iterate_pages(self, url: str, params: Optional[dict[str, Any]]=None) -> AsyncIterable[dict[str, Any]]:
        """Iterates all the entries of a paged endpoint"""
        request_params = {}
        if params is not None:
            request_params.update(params)
        request_params["currentPageSize"] = _PAGE_SIZE

        current_page = 1
        has_next = True
        while has_next:
            request_params["currentPage"] = current_page
            response = await self.request("get", url, request_params)
            
            # Setup next page request
            current_page = int(response['currentPage']) + 1
            current_size = int(response['currentSize'])
            total_rows = int(response['totalRows'])
            has_next = total_rows > current_page * current_size

            data: list[dict[str, Any]] = response['data']
            for item in data:
                yield item

    async def request(self, method: str, url: str, params=None, payload=None) -> Any:
        """Perform a request specific to the controlller, with authentication"""

        if not await self._check_login():
            await self.login()

        return await self._do_request(method, url, params=params, payload=payload)

    async def _do_request(
        self, method: str, url: str, params=None, payload=None
    ) -> Any:
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
                        content = await response.json(encoding="utf-8")
                        self._check_application_errors(content)

                    raise RequestFailed(response.status, "HTTP Request Error")

                # If something goes wrong with the login session, Omada requests return "success", and a login page. :/
                if response.content_type != "application/json":
                    raise LoginSessionClosed()

                content = await response.json(encoding="utf-8")
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
        if not "errorCode" in response:
            raise RequestFailed(-30109, "Unexpected response: " + str(response))
        if response["errorCode"] == 0:
            return
        if response["errorCode"] == -30109:
            raise LoginFailed(response["errorCode"], response["msg"])
        raise RequestFailed(response["errorCode"], response["msg"])
