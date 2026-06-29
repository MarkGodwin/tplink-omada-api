"""Tests for the low-level Omada API connection."""

import asyncio
import time
from typing import Any

from tplink_omada_client.omadaapiconnection import OmadaApiConnection


class FakeResponse:
    """Minimal aiohttp response stand-in."""

    def __init__(self, content_type: str, payload: dict[str, Any] | None = None) -> None:
        self.status = 200
        self.content_type = content_type
        self._payload = payload or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def json(self, encoding: str = "utf-8") -> dict[str, Any]:
        return self._payload


class FakeSession:
    """Minimal aiohttp session stand-in."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, str, dict[str, str]]] = []

    def request(self, method: str, url: str, **kwargs) -> FakeResponse:
        self.requests.append((method, url, kwargs.get("headers", {})))
        return self.responses.pop(0)


def test_authenticated_request_relogs_after_closed_session():
    """Authenticated requests retry once when Omada invalidates the session."""
    session = FakeSession(
        [
            FakeResponse("text/html"),
            FakeResponse(
                "application/json",
                {
                    "errorCode": 0,
                    "result": {
                        "controllerVer": "6.2.10.17",
                        "omadacId": "controller-id",
                    },
                },
            ),
            FakeResponse(
                "application/json",
                {"errorCode": 0, "result": {"token": "new-token"}},
            ),
            FakeResponse("application/json", {"errorCode": 0, "result": {"ok": True}}),
        ]
    )
    connection = OmadaApiConnection(
        "https://omada.example:8043", "user", "pass", session
    )
    connection._controller_id = "controller-id"
    connection._csrf_token = "old-token"
    connection._last_logon = time.time()

    result = asyncio.run(connection.request("get", "https://omada.example/request"))

    assert result == {"ok": True}
    assert connection._csrf_token == "new-token"
    assert session.requests[0][2]["Csrf-Token"] == "old-token"
    assert session.requests[-1][2]["Csrf-Token"] == "new-token"
