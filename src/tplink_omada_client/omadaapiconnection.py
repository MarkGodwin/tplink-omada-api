"""Internal Omada API client."""

import re
import time
from collections.abc import AsyncIterable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlsplit

from aiohttp import CookieJar, Payload, client_exceptions
from aiohttp.client import ClientSession
from awesomeversion import AwesomeVersion

from .definitions import OmadaControllerInfo
from .exceptions import (
    BadControllerUrl,
    ConnectionFailed,
    LoginFailed,
    LoginSessionClosed,
    RequestFailed,
    UnsupportedControllerVersion,
)

_PAGE_SIZE: int = 100


@dataclass
class _RequestObservation:
    """Per-operation handoff history; authentication calls do not share it."""

    _attempts: list[str] = field(default_factory=list)

    @property
    def attempt_count(self) -> int:
        return len(self._attempts)

    @property
    def has_unresolved_attempt(self) -> bool:
        return "unresolved" in self._attempts

    @property
    def acknowledged(self) -> bool:
        return "acknowledged" in self._attempts

    def acknowledge(self, attempt: int, content: Any) -> None:
        if not isinstance(content, dict) or type(content.get("errorCode")) is not int or content["errorCode"] != 0:
            raise RequestFailed(-30109, "Unexpected mutation acknowledgement")
        self._attempts[attempt] = "acknowledged"


class OmadaApiConnection:
    """Low level Omada API client."""

    _own_session: bool
    _controller_id: str
    _controller_version: str | None = None
    _csrf_token: str | None
    _last_logon: float

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        websession: ClientSession | None = None,
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
            jar = None if re.fullmatch(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", self._host) is None else CookieJar(unsafe=True)
            self._session = ClientSession(cookie_jar=jar)
        return self._session

    async def __aenter__(self):
        try:
            await self.login()
            return self
        except Exception:
            if self._own_session:
                await self.close()
            raise

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

        self._clear_login_state()

        version, controller_id = await self._get_controller_info()

        if AwesomeVersion(version) < AwesomeVersion("5.1.0"):
            raise UnsupportedControllerVersion(version)

        self._controller_id = controller_id
        self._controller_version = version

        auth = {"username": self._username, "password": self._password}
        response = await self._do_request("post", self.format_url("login"), json=auth)

        self._csrf_token = response["token"]
        self._last_logon = time.time()

        return self._controller_id

    def _clear_login_state(self) -> None:
        """Clear authentication state associated with this controller."""
        self._csrf_token = None
        if self._session is not None:
            self._session.cookie_jar.clear_domain(self._host)

    async def _check_login(self) -> bool:
        if self._csrf_token is None:
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
        except Exception:  # noqa: BLE001 - retain failed-status re-login policy, but not BaseException cancellation
            return False

    async def get_controller_info(self) -> OmadaControllerInfo:
        """Get Omada controller diagnostic information unauthenticated."""
        response = await self._do_request("get", urljoin(self._url, "/api/info"))
        return OmadaControllerInfo(response)

    async def _get_controller_info(self) -> tuple[str, str]:
        """Get Omada controller version and Id (unauthenticated)."""
        info = await self.get_controller_info()

        return (info.controller_version, info.omadac_id)

    def format_url(self, end_point: str, site: str | None = None) -> str:
        """Get a REST url for the controller action"""

        if site:
            end_point = f"sites/{site}/{end_point}"

        return urljoin(self._url, f"/{self._controller_id}/api/v2/{end_point}")

    def format_openapi_url(self, end_point: str, version: str = "v1", site: str | None = None) -> str:
        """Get a REST url for the controller action"""

        if site:
            end_point = f"sites/{site}/{end_point}"

        return urljoin(self._url, f"/openapi/{version}/{self._controller_id}/{end_point}")

    async def iterate_pages(self, url: str, params: dict[str, Any] | None = None) -> AsyncIterable[dict[str, Any]]:
        """Iterates all the entries of a paged endpoint using GET with query parameters (old API)"""
        request_params = {}
        if params is not None:
            request_params.update(params)
        actual_page_size = _PAGE_SIZE

        current_page = 1
        has_next = True
        while has_next:
            request_params["currentPageSize"] = actual_page_size
            request_params["currentPage"] = current_page
            response = await self.request("get", url, request_params)

            # Setup next page request
            actual_page_size = int(response["currentSize"])
            total_rows = int(response["totalRows"])
            has_next = total_rows > current_page * actual_page_size
            current_page += 1

            data: list[dict[str, Any]] = response["data"]
            for item in data:
                yield item

    async def iterate_pages_openapi(self, url: str, body: dict[str, Any] | None = None) -> AsyncIterable[dict[str, Any]]:
        """Iterates all the entries of a paged endpoint using POST with JSON body (OpenAPI v2)"""
        request_body = {}
        if body is not None:
            request_body.update(body)
        actual_page_size = _PAGE_SIZE

        current_page = 1
        has_next = True
        while has_next:
            request_body["pageSize"] = actual_page_size
            request_body["page"] = current_page
            response = await self.request("post", url, json=request_body)

            # Setup next page request
            actual_page_size = int(response["currentSize"])
            total_rows = int(response["totalRows"])
            has_next = total_rows > current_page * actual_page_size
            current_page += 1

            data: list[dict[str, Any]] = response["data"]
            for item in data:
                yield item

    async def iterate_pages_openapi_get(self, url: str, params: dict[str, Any] | None = None) -> AsyncIterable[dict[str, Any]]:
        """Iterates all the entries of a paged endpoint using GET with query parameters (OpenAPI v2)"""
        request_params = {}
        if params is not None:
            request_params.update(params)
        actual_page_size = _PAGE_SIZE

        current_page = 1
        has_next = True
        while has_next:
            request_params["pageSize"] = actual_page_size
            request_params["page"] = current_page
            response = await self.request("get", url, params=request_params)

            # Setup next page request
            actual_page_size = int(response["currentSize"])
            total_rows = int(response["totalRows"])
            has_next = total_rows > current_page * actual_page_size
            current_page += 1

            data: list[dict[str, Any]] = response["data"]
            for item in data:
                yield item

    async def request(
        self, method: str, url: str, params=None, json=None, data: Payload | None = None,
        *, observation: _RequestObservation | None = None,
    ) -> Any:
        """Perform an authenticated request, optionally observing its handoffs."""

        if not await self._check_login():
            await self.login()

        kwargs: dict[str, Any] = {"params": params, "json": json, "data": data}
        if observation is not None:
            kwargs["observation"] = observation
        try:
            return await self._do_request(method, url, **kwargs)
        except (LoginFailed, LoginSessionClosed):
            await self.login()
            return await self._do_request(method, url, **kwargs)

    async def get_controller_version(self) -> AwesomeVersion:
        """Get the controller version as an AwesomeVersion object."""
        version = self._controller_version
        if version is None:
            version, _ = await self._get_controller_info()
        return AwesomeVersion(version)

    async def _do_request(
        self, method: str, url: str, params=None, json=None, data: Payload | None = None,
        *, observation: _RequestObservation | None = None,
    ) -> Any:
        """Perform a request on the controller, and unpack the response."""

        session = await self._get_session()

        # Note: Auth happens via cookies, set during the login command, but we also get a CSRF token
        # which we need to push back
        headers = {}
        if self._csrf_token:
            headers["Csrf-Token"] = self._csrf_token
            headers["Omada-Request-Source"] = "web-local"
            headers["Referer"] = self._url + "/"
            headers["Origin"] = self._url

        attempt = 0
        if observation is not None:
            attempt = observation.attempt_count
            observation._attempts.append("unresolved")

        try:
            async with session.request(
                method,
                url,
                params=params,
                headers=headers,
                json=json,
                data=data,
                ssl=self._verify_ssl,
            ) as response:
                return await self._unpack_response(response, observation, attempt)

        except RequestFailed as err:
            if observation is not None and err.application_rejection:
                observation._attempts[attempt] = "rejected"
            raise
        except client_exceptions.InvalidURL as err:
            raise BadControllerUrl(err) from err
        except client_exceptions.ClientConnectionError as err:
            raise ConnectionFailed(err) from err
        except client_exceptions.ClientError as err:
            raise RequestFailed(0, f"Unexpected error: {err}") from None

    async def _unpack_response(self, response, observation: _RequestObservation | None, attempt: int) -> Any:
        """Validate and unpack an HTTP response, retaining application provenance."""
        if response.status != 200:
            if response.content_type == "application/json":
                self._check_application_errors(await response.json(encoding="utf-8"))
            raise RequestFailed(response.status, "HTTP Request Error")
        if response.content_type != "application/json":
            raise LoginSessionClosed()
        content = await response.json(encoding="utf-8")
        self._check_application_errors(content)
        if observation is not None:
            observation.acknowledge(attempt, content)
        if "result" in content:
            return content["result"]
        return content

    def _check_application_errors(self, response):
        if not isinstance(response, dict):
            return
        if "errorCode" not in response:
            raise RequestFailed(-30109, "Unexpected response: " + str(response))
        if response["errorCode"] == 0:
            return
        if response["errorCode"] == -30109:
            raise LoginFailed(
                response["errorCode"], response["msg"],
                application_rejection=type(response["errorCode"]) is int,
            )
        raise RequestFailed(
            response["errorCode"], response["msg"],
            application_rejection=type(response["errorCode"]) is int,
        )
