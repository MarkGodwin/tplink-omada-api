"""Tests for OmadaClient controller endpoints."""

# pylint: disable=protected-access

import asyncio
from typing import Any

from awesomeversion import AwesomeVersion

from tplink_omada_client.definitions import (
    OmadaControllerStatus,
    OmadaControllerUpdateInfo,
    OmadaHardwareUpgradeStatus,
)
from tplink_omada_client.omadaclient import OmadaClient


class FakeApi:
    """Minimal API stand-in for OmadaClient controller tests."""

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.response = response or {}
        self.requests = []
        self.urls = []

    def format_url(self, end_point: str, site: str | None = None) -> str:
        """Return a predictable URL for assertions."""
        assert site is None
        url = f"api/v2/{end_point}"
        self.urls.append(url)
        return url

    async def get_controller_version(self):
        """Use the legacy endpoint for this controller test fixture."""
        return AwesomeVersion("6.2.10.17")

    async def request(self, method: str, url: str, params=None, json=None, data=None):
        """Record requests and return the configured response."""
        self.requests.append((method, url, params, json, data))
        return self.response


def _client_with_api(api: FakeApi) -> OmadaClient:
    """Create an OmadaClient that uses the fake API."""
    client = OmadaClient("https://omada.example", "user", "pass")
    client._api = api
    return client


def test_get_controller_status_uses_controller_status_endpoint():
    """Controller status uses the legacy controller status endpoint."""
    api = FakeApi({
        "name": "Main Controller",
        "macAddress": "00-11-22-33-44-55",
        "upTime": 123,
        "controllerVersion": "6.2.10.17",
        "model": "OC200",
    })
    client = _client_with_api(api)

    status = asyncio.run(client.get_controller_status())

    assert isinstance(status, OmadaControllerStatus)
    assert status.name == "Main Controller"
    assert api.urls == ["api/v2/maintenance/controllerStatus"]
    assert api.requests == [("get", "api/v2/maintenance/controllerStatus", None, None, None)]


def test_check_firmware_updates_uses_controller_update_info_endpoint():
    """Controller update checks use the controller update notification endpoint."""
    api = FakeApi({
        "hardware": {
            "upgrade": True,
            "currentVersion": "1.0.0",
            "latestVersion": "1.0.1",
        }
    })
    client = _client_with_api(api)

    update_info = asyncio.run(client.check_firmware_updates())

    assert isinstance(update_info, OmadaControllerUpdateInfo)
    assert update_info.hardware is not None
    assert api.urls == ["api/v2/controller/notification/updateInfo"]
    assert api.requests == [("get", "api/v2/controller/notification/updateInfo", None, None, None)]


def test_install_controller_firmware_posts_target_version():
    """Controller firmware install posts the requested target version."""
    api = FakeApi()
    client = _client_with_api(api)

    result = asyncio.run(client.install_controller_firmware("1.0.1"))

    assert result is True
    assert api.urls == ["api/v2/cmd/upgradeFirmware"]
    assert api.requests == [
        ("post", "api/v2/cmd/upgradeFirmware", None, {"targetVersion": "1.0.1"}, None),
    ]


def test_get_controller_upgrade_status_uses_hardware_upgrade_status_endpoint():
    """Controller upgrade status uses the hardware upgrade status endpoint."""
    api = FakeApi({"upgradeStatus": 1, "downloadProgress": 25})
    client = _client_with_api(api)

    status = asyncio.run(client.get_controller_upgrade_status())

    assert isinstance(status, OmadaHardwareUpgradeStatus)
    assert status.upgrade_status == 1
    assert status.download_progress == 25
    assert api.urls == ["api/v2/maintenance/hardware/upgradeStatus"]
    assert api.requests == [("get", "api/v2/maintenance/hardware/upgradeStatus", None, None, None)]
