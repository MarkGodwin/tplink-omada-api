"""Tests for switch port profile handling."""

import asyncio

from awesomeversion import AwesomeVersion

from tplink_omada_client.definitions import Eth802Dot1X, LinkDuplex, LinkSpeed, PoEMode
from tplink_omada_client.devices import OmadaPortProfile, OmadaSwitchPortDetails
from tplink_omada_client.omadaapiconnection import OmadaApiConnection
from tplink_omada_client.omadasiteclient import OmadaSiteClient, PortProfileOverrides, SwitchPortSettings


def _port_data(profile_override: bool = False) -> dict:
    return {
        "id": "port-id",
        "port": 1,
        "name": "Port 1",
        "profileId": "profile-1",
        "profileName": "Default",
        "profileOverrideEnable": profile_override,
        "supportPoe": True,
        "poe": PoEMode.ENABLED,
        "maxSpeed": LinkSpeed.SPEED_1_GBPS,
        "linkSpeed": LinkSpeed.SPEED_AUTO,
        "duplex": LinkDuplex.AUTO,
        "type": 0,
        "operation": "switching",
        "disable": False,
        "portStatus": {"linkStatus": 0, "poe": False},
        "bandWidthCtrlType": 0,
        "tagIds": [],
    }


def _profile_data(dot1x=Eth802Dot1X.AUTO) -> dict:
    result = {
        "id": "profile-1",
        "name": "Default",
        "poe": PoEMode.ENABLED,
        "portIsolationEnable": False,
        "lldpMedEnable": True,
        "bandWidthCtrlType": 0,
        "spanningTreeEnable": False,
        "loopbackDetectEnable": True,
        "eeeEnable": False,
        "flowControlEnable": False,
        "loopbackDetectVlanBasedEnable": False,
        "dhcpL2RelaySettings": {"enable": False},
        "type": 2,
    }
    if dot1x is not None:
        result["dot1x"] = dot1x
    return result


class FakeApi:
    def __init__(self, version: str = "6.2.0.0", profiles: list[dict] | None = None) -> None:
        self.version = AwesomeVersion(version)
        self.profiles = profiles or [_profile_data()]
        self.requests = []
        self.openapi_urls = []
        self.legacy_urls = []

    async def get_controller_version(self) -> AwesomeVersion:
        return self.version

    def format_openapi_url(self, end_point: str, version: str = "v1", site: str | None = None) -> str:
        url = f"openapi/{version}/{site}/{end_point}"
        self.openapi_urls.append(url)
        return url

    def format_url(self, end_point: str, site: str | None = None) -> str:
        url = f"api/{site}/{end_point}"
        self.legacy_urls.append(url)
        return url

    async def iterate_pages_openapi_get(self, url: str, params: dict | None = None):
        self.requests.append(("iterate_pages_openapi_get", url, params))
        for profile in self.profiles:
            yield profile

    async def request(self, method: str, url: str, params=None, json=None, data=None):
        self.requests.append((method, url, params, json, data))
        if method == "get" and url.endswith("profileSummary"):
            return {"data": self.profiles}
        if method == "get" and url.endswith("/ports/1"):
            return _port_data()
        if method == "patch":
            return {}
        raise AssertionError(f"Unexpected request: {method} {url}")


class FakePagedApi:
    def __init__(self) -> None:
        self.requests = []

    async def request(self, method: str, url: str, params=None):
        self.requests.append((method, url, params.copy()))
        page = params["page"]
        return {
            "totalRows": 2,
            "currentSize": 1,
            "data": [{"id": f"profile-{page}"}],
        }


def test_port_profile_dot1x_defaults_to_unknown_when_missing():
    profile = OmadaPortProfile(_profile_data(dot1x=None))
    port = OmadaSwitchPortDetails(_port_data())

    assert profile.eth_802_1x_control == Eth802Dot1X.UNKNOWN
    assert port.eth_802_1x_control == Eth802Dot1X.UNKNOWN


def test_openapi_get_paginator_uses_page_and_page_size_params():
    api = FakePagedApi()

    profiles = asyncio.run(_collect_openapi_get_pages(api))

    assert profiles == [{"id": "profile-1"}, {"id": "profile-2"}]
    assert api.requests == [
        ("get", "openapi/v2/site-id/lan-profiles", {"pageSize": 100, "page": 1}),
        ("get", "openapi/v2/site-id/lan-profiles", {"pageSize": 1, "page": 2}),
    ]


async def _collect_openapi_get_pages(api: FakePagedApi) -> list[dict]:
    return [
        item
        async for item in OmadaApiConnection.iterate_pages_openapi_get(
            api,
            "openapi/v2/site-id/lan-profiles",
        )
    ]


def test_get_port_profiles_uses_openapi_lan_profiles_for_modern_controllers():
    api = FakeApi(profiles=[_profile_data()])
    client = OmadaSiteClient("site-id", api)

    profiles = asyncio.run(client.get_port_profiles())

    assert len(profiles) == 1
    assert profiles[0].profile_id == "profile-1"
    assert profiles[0].eth_802_1x_control == Eth802Dot1X.AUTO
    assert api.openapi_urls == ["openapi/v2/site-id/lan-profiles"]
    assert api.requests == [("iterate_pages_openapi_get", "openapi/v2/site-id/lan-profiles", None)]


def test_get_port_profiles_uses_legacy_profile_summary_before_6_2():
    api = FakeApi(version="6.1.0", profiles=[_profile_data()])
    client = OmadaSiteClient("site-id", api)

    profiles = asyncio.run(client.get_port_profiles())

    assert len(profiles) == 1
    assert profiles[0].profile_id == "profile-1"
    assert api.openapi_urls == []
    assert api.requests == [
        ("get", "api/site-id/setting/lan/profileSummary", None, None, None),
    ]


def test_update_switch_port_poe_override_preserves_profile_dot1x():
    api = FakeApi(profiles=[_profile_data(dot1x=Eth802Dot1X.FORCE_AUTHORIZED)])
    client = OmadaSiteClient("site-id", api)
    port = OmadaSwitchPortDetails(_port_data())

    asyncio.run(
        client.update_switch_port(
            "switch-mac",
            port,
            SwitchPortSettings(
                profile_override_enabled=True,
                profile_overrides=PortProfileOverrides(enable_poe=False),
            ),
        )
    )

    patch_requests = [request for request in api.requests if request[0] == "patch"]
    assert len(patch_requests) == 1
    payload = patch_requests[0][3]
    assert payload["poe"] == PoEMode.DISABLED
    assert payload["dot1x"] == Eth802Dot1X.FORCE_AUTHORIZED


def test_update_switch_port_poe_override_omits_missing_dot1x():
    api = FakeApi(profiles=[_profile_data(dot1x=None)])
    client = OmadaSiteClient("site-id", api)
    port = OmadaSwitchPortDetails(_port_data())

    asyncio.run(
        client.update_switch_port(
            "switch-mac",
            port,
            SwitchPortSettings(
                profile_override_enabled=True,
                profile_overrides=PortProfileOverrides(enable_poe=False),
            ),
        )
    )

    patch_requests = [request for request in api.requests if request[0] == "patch"]
    assert len(patch_requests) == 1
    payload = patch_requests[0][3]
    assert payload["poe"] == PoEMode.DISABLED
    assert "dot1x" not in payload
