"""Tests for the low-level Omada API connection."""

import asyncio
import time
from typing import Any

import pytest

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


class FakeSession[ResponseT: FakeResponse | BaseException]:
    """Minimal aiohttp session stand-in."""

    def __init__(self, responses: list[ResponseT]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.cookie_jar = FakeCookieJar()

    def request(self, method: str, url: str, **kwargs) -> ResponseT:
        self.requests.append((method, url, kwargs.get("headers", {})))
        return self.responses.pop(0)


class FakeCookieJar:
    """Minimal aiohttp cookie jar stand-in."""

    def __init__(self) -> None:
        self.cleared_domains: list[str] = []

    def clear_domain(self, domain: str) -> None:
        self.cleared_domains.append(domain)


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
    assert session.cookie_jar.cleared_domains == ["omada.example"]


def test_authenticated_request_clears_stale_login_state_before_login():
    """A failed login-status check does not leak stale authentication into login."""
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
    connection._last_logon = 0

    result = asyncio.run(connection.request("get", "https://omada.example/request"))

    assert result == {"ok": True}
    assert session.requests[0][2]["Csrf-Token"] == "old-token"
    assert "Csrf-Token" not in session.requests[1][2]
    assert "Csrf-Token" not in session.requests[2][2]
    assert session.requests[3][2]["Csrf-Token"] == "new-token"
    assert session.cookie_jar.cleared_domains == ["omada.example"]


class ScriptedSession(FakeSession[FakeResponse | BaseException]):
    """Exercise the real transport using only local response/exception scripts."""

    def request(self, method: str, url: str, **kwargs) -> FakeResponse:
        self.requests.append((method, url, kwargs.get("headers", {})))
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def _connection(session, *, stale=False):
    connection = OmadaApiConnection("https://omada.example", "user", "pass", session)
    connection._controller_id = "controller-id"
    connection._csrf_token = "old-token"
    connection._last_logon = 0 if stale else time.time()
    return connection


def _login_responses():
    return [
        FakeResponse("application/json", {"errorCode": 0, "result": {"controllerVer": "6.2.0", "omadacId": "controller-id"}}),
        FakeResponse("application/json", {"errorCode": 0, "result": {"token": "new-token"}}),
    ]


def test_cancelled_login_status_never_logs_in_or_mutates():
    async def scenario():
        entered = asyncio.Event()

        class WaitingResponse(FakeResponse):
            async def __aenter__(self) -> FakeResponse:
                entered.set()
                await asyncio.Event().wait()
                return self

        session = ScriptedSession([WaitingResponse("application/json"), *_login_responses(),
                                   FakeResponse("application/json", {"errorCode": 0})])
        connection = _connection(session, stale=True)
        task = asyncio.create_task(connection.request("patch", "https://omada.example/group"))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert [row[0] for row in session.requests] == ["get"]

    asyncio.run(scenario())


@pytest.mark.parametrize("during_login, expected_attempts", [(True, 0), (False, 1)])
def test_timeout_phase_tracks_real_session_handoff(during_login, expected_attempts):
    from tplink_omada_client.omadaapiconnection import _RequestObservation

    session = ScriptedSession([TimeoutError("same failure")])
    connection = _connection(session)
    if during_login:
        connection._csrf_token = None
    observation = _RequestObservation()
    with pytest.raises(TimeoutError, match="same failure"):
        asyncio.run(connection.request("patch", "https://omada.example/group", observation=observation))
    assert observation.attempt_count == expected_attempts
    assert observation.has_unresolved_attempt is (not during_login)


@pytest.mark.parametrize("payload, rejected", [({"errorCode": 42, "msg": "in use"}, True),
                                              ({"msg": "not an acknowledgement"}, False)])
def test_application_rejection_is_not_inferred_from_exception_class(payload, rejected):
    from tplink_omada_client.exceptions import RequestFailed
    from tplink_omada_client.omadaapiconnection import _RequestObservation

    session = ScriptedSession([FakeResponse("application/json", payload)])
    observation = _RequestObservation()
    with pytest.raises(RequestFailed) as caught:
        asyncio.run(_connection(session).request("post", "https://omada.example/group", observation=observation))
    assert observation.attempt_count == 1
    assert observation.has_unresolved_attempt is (not rejected)
    assert caught.value.application_rejection is rejected


def test_rejection_after_unresolved_attempt_does_not_erase_uncertainty():
    from tplink_omada_client.exceptions import RequestFailed
    from tplink_omada_client.omadaapiconnection import _RequestObservation

    session = ScriptedSession([FakeResponse("text/html"), *_login_responses(),
                               FakeResponse("application/json", {"errorCode": 42, "msg": "in use"})])
    observation = _RequestObservation()
    with pytest.raises(RequestFailed):
        asyncio.run(_connection(session).request("post", "https://omada.example/group", observation=observation))
    assert observation.attempt_count == 2
    assert observation.has_unresolved_attempt
    assert [row[0] for row in session.requests] == ["post", "get", "post", "post"]


def test_observation_is_operation_local_and_acknowledges_success():
    from tplink_omada_client.omadaapiconnection import _RequestObservation

    async def scenario():
        session = ScriptedSession([FakeResponse("application/json", {"errorCode": 0}), TimeoutError("lost")])
        connection = _connection(session)
        first, second = _RequestObservation(), _RequestObservation()
        results = await asyncio.gather(
            connection.request("post", "https://omada.example/first", observation=first),
            connection.request("post", "https://omada.example/second", observation=second),
            return_exceptions=True,
        )
        assert results[0] == {"errorCode": 0}
        assert isinstance(results[1], TimeoutError)
        assert (first.attempt_count, first.has_unresolved_attempt) == (1, False)
        assert (second.attempt_count, second.has_unresolved_attempt) == (1, True)

    asyncio.run(scenario())
