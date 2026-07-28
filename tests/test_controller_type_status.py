"""Tests for controller type and status information."""

from unittest.mock import AsyncMock, Mock

import pytest

from tplink_omada_client import OmadaClient
from tplink_omada_client.definitions import (
    OmadaControllerStatus,
    OmadaControllerType,
)


@pytest.mark.parametrize(
    ("is_soft_controller", "expected"),
    [
        (True, True),
        (False, False),
    ],
)
def test_controller_type_data(
    is_soft_controller: bool,
    expected: bool,
) -> None:
    """Controller type exposes whether the controller is software based."""
    controller_type = OmadaControllerType(
        {"isSoftController": is_soft_controller}
    )

    assert controller_type.is_soft_controller is expected


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("OC200", "OC200"),
        ("  OC300  ", "OC300"),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_controller_status_data(
    model: str | None,
    expected: str | None,
) -> None:
    """Controller status exposes its standard fields and optional model."""
    data = {
        "name": "Omada RealSW",
        "macAddress": "FE-54-00-76-76-34",
        "upTime": 1667366874,
        "controllerVersion": "6.2.10.17",
    }
    if model is not None:
        data["model"] = model

    controller_status = OmadaControllerStatus(data)

    assert controller_status.name == "Omada RealSW"
    assert controller_status.mac_address == "FE-54-00-76-76-34"
    assert controller_status.uptime == 1667366874
    assert controller_status.controller_version == "6.2.10.17"
    assert controller_status.model == expected


@pytest.mark.asyncio
async def test_get_controller_type() -> None:
    """Controller type is requested from the public client method."""
    client = OmadaClient("https://omada.test", "user", "password")
    client._api = Mock()
    client._api.format_url.return_value = "controller-type-url"
    client._api.request = AsyncMock(
        return_value={"isSoftController": True}
    )

    result = await client.get_controller_type()

    assert result.is_soft_controller is True
    client._api.format_url.assert_called_once_with("anon/controllerType")
    client._api.request.assert_awaited_once_with(
        "get",
        "controller-type-url",
    )


@pytest.mark.asyncio
async def test_get_controller_status() -> None:
    """Controller status is requested from the public client method."""
    client = OmadaClient("https://omada.test", "user", "password")
    client._api = Mock()
    client._api.format_url.return_value = "controller-status-url"
    client._api.request = AsyncMock(
        return_value={
            "name": "Omada RealSW",
            "macAddress": "FE-54-00-76-76-34",
            "upTime": 1667366874,
            "controllerVersion": "6.2.10.17",
            "model": "OC200",
        }
    )

    result = await client.get_controller_status()

    assert result.name == "Omada RealSW"
    assert result.mac_address == "FE-54-00-76-76-34"
    assert result.uptime == 1667366874
    assert result.controller_version == "6.2.10.17"
    assert result.model == "OC200"
    client._api.format_url.assert_called_once_with(
        "maintenance/controllerStatus"
    )
    client._api.request.assert_awaited_once_with(
        "get",
        "controller-status-url",
    )
