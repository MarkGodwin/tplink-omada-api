"""Tests for LAN-network listing and VLAN-only lifecycle on OmadaSiteClient."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from awesomeversion import AwesomeVersion

from tplink_omada_client.networks import LanNetwork
from tplink_omada_client.omadasiteclient import OmadaSiteClient

# Version parameters exercise the captured contract, not live controller compatibility.
VLAN_CONTROLLER_VERSIONS = ["5.9.9", "5.15.8.11", "5.15.8.12", "5.15.8.13", "6.0.0", "6.2.0.0"]


async def _async_gen(items):
    """Turn an iterable into an async generator."""
    for item in items:
        yield item


@pytest.fixture
def site_client():
    api = MagicMock()
    api.format_url = MagicMock(side_effect=lambda path, site=None: f"/api/v2/sites/{site}/{path}")
    api.get_controller_version = AsyncMock(return_value=AwesomeVersion("6.2.0.0"))
    return OmadaSiteClient("site-id", api)


@pytest.mark.asyncio
async def test_get_lan_networks_uses_internal_endpoint_and_preserves_page_order(site_client):
    """LAN networks use the internal settings endpoint and legacy pagination."""
    response = [
        {
            "id": "network-1",
            "name": "Management",
            "purpose": "interface",
            "vlan": 1,
            "gatewaySubnet": "192.168.0.1/24",
            "dhcpSettings": {"enable": True},
        },
        {
            "id": "network-2",
            "name": "IOT",
            "purpose": "interface",
            "vlan": 30,
            "gatewaySubnet": "192.168.30.1/24",
            "dhcpSettings": {"enable": False},
        },
    ]
    url = "/api/v2/sites/site-id/setting/lan/networks"
    site_client._api.iterate_pages = MagicMock(return_value=_async_gen(response))

    networks = await site_client.get_lan_networks()

    site_client._api.format_url.assert_called_once_with("setting/lan/networks", "site-id")
    site_client._api.iterate_pages.assert_called_once_with(url)
    assert [network.name for network in networks] == ["Management", "IOT"]
    assert all(isinstance(network, LanNetwork) for network in networks)
    assert networks[1].dhcp_enabled is False


@pytest.fixture
def vlan_site(site_client):
    import json
    from pathlib import Path

    site_client._api.request = AsyncMock(return_value={"errorCode": 0, "msg": "OK"})
    site_client._vlan_fixture = json.loads((Path(__file__).parent / "fixtures/vlan_management.json").read_text())
    return site_client


@pytest.mark.asyncio
@pytest.mark.parametrize("version", VLAN_CONTROLLER_VERSIONS)
async def test_vlan_create_uses_range_endpoint_and_reads_acknowledgement_back(vlan_site, version):
    from tplink_omada_client.vlans import VlanCreate

    vlan_site._api.get_controller_version.return_value = AwesomeVersion(version)

    fixture = vlan_site._vlan_fixture
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[], [LanNetwork(fixture["network"])]])
    result = await vlan_site.create_vlan(VlanCreate("example-vlan", 3990))
    assert result.id == "example-network-id"
    vlan_site._api.request.assert_awaited_once_with("post", "/api/v2/sites/site-id/setting/lan/vlans", json=fixture["create"]["payload"])
    assert vlan_site.get_lan_networks.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("version", VLAN_CONTROLLER_VERSIONS)
async def test_vlan_update_preserves_full_settings_and_reads_back(vlan_site, version):
    from tplink_omada_client.vlans import VlanUpdate

    vlan_site._api.get_controller_version.return_value = AwesomeVersion(version)

    before = LanNetwork(vlan_site._vlan_fixture["network"])
    after = LanNetwork(before.raw_data | {"name": "renamed"})
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[before], [after]])
    result = await vlan_site.update_vlan(before.id, VlanUpdate(name="renamed"))
    assert result.name == "renamed"
    args, kwargs = vlan_site._api.request.call_args
    assert args == ("patch", "/api/v2/sites/site-id/setting/lan/networks/example-network-id")
    assert kwargs["json"]["vlan"] == 3990
    assert kwargs["json"]["dhcpGuard"] == {"enable": False}
    assert "site" not in kwargs["json"]


@pytest.mark.asyncio
@pytest.mark.parametrize("version", VLAN_CONTROLLER_VERSIONS)
async def test_vlan_delete_uses_exact_id_without_body_and_verifies_absence(vlan_site, version):
    vlan_site._api.get_controller_version.return_value = AwesomeVersion(version)
    network = LanNetwork(vlan_site._vlan_fixture["network"])
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[network], []])
    await vlan_site.delete_vlan(network.name)
    vlan_site._api.request.assert_awaited_once_with("delete", "/api/v2/sites/site-id/setting/lan/networks/example-network-id")


@pytest.mark.asyncio
@pytest.mark.parametrize("version", VLAN_CONTROLLER_VERSIONS)
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_vlan_preview_never_mutates(vlan_site, operation, version):
    from tplink_omada_client.vlans import VlanCreate, VlanUpdate

    vlan_site._api.get_controller_version.return_value = AwesomeVersion(version)

    network = LanNetwork(vlan_site._vlan_fixture["network"])
    vlan_site.get_lan_networks = AsyncMock(return_value=[] if operation == "create" else [network])
    if operation == "create":
        assert (await vlan_site.preview_vlan_create(VlanCreate("example", 20)))["vlans"] == "20"
    elif operation == "update":
        current, payload = await vlan_site.preview_vlan_update(network.id, VlanUpdate(name="renamed"))
        assert current.id == network.id and payload["name"] == "renamed"
    else:
        assert (await vlan_site.preview_vlan_delete(network.id)).id == network.id
    vlan_site._api.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_vlan_create_rejects_existing_name_or_id(vlan_site):
    from tplink_omada_client.vlans import VlanCreate

    vlan_site.get_lan_networks = AsyncMock(return_value=[LanNetwork(vlan_site._vlan_fixture["network"])])
    for request in [VlanCreate("other", 3990), VlanCreate("example-vlan", 20)]:
        with pytest.raises(ValueError, match="already"):
            await vlan_site.create_vlan(request)
    vlan_site._api.request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("changes", [{"primary": True}, {"vlan": 1}, {"purpose": "interface"}])
async def test_vlan_delete_refuses_protected_or_routed_networks(vlan_site, changes):
    network = LanNetwork(vlan_site._vlan_fixture["network"] | changes)
    vlan_site.get_lan_networks = AsyncMock(return_value=[network])
    with pytest.raises(ValueError):
        await vlan_site.delete_vlan(network.id)
    vlan_site._api.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_vlan_update_noop_does_not_write(vlan_site):
    from tplink_omada_client.vlans import VlanUpdate

    network = LanNetwork(vlan_site._vlan_fixture["network"])
    vlan_site.get_lan_networks = AsyncMock(return_value=[network])
    assert (await vlan_site.update_vlan(network.id, VlanUpdate(name=network.name))).id == network.id
    vlan_site._api.request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_vlan_readback_mismatch_is_not_success_and_never_retries_write(vlan_site, operation):
    from tplink_omada_client.exceptions import OmadaClientException
    from tplink_omada_client.vlans import VlanCreate, VlanUpdate

    network = LanNetwork(vlan_site._vlan_fixture["network"])
    if operation == "create":
        vlan_site.get_lan_networks = AsyncMock(side_effect=[[], []])
        action = vlan_site.create_vlan(VlanCreate("example-vlan", 3990))
    elif operation == "update":
        vlan_site.get_lan_networks = AsyncMock(return_value=[network])
        action = vlan_site.update_vlan(network.id, VlanUpdate(name="renamed"))
    else:
        vlan_site.get_lan_networks = AsyncMock(return_value=[network])
        action = vlan_site.delete_vlan(network.id)
    with pytest.raises(OmadaClientException, match="read-back"):
        await action
    assert vlan_site._api.request.await_count == 1


@pytest.mark.asyncio
async def test_vlan_controller_error_propagates_without_readback_or_cleanup(vlan_site):
    from tplink_omada_client.exceptions import RequestFailed
    from tplink_omada_client.vlans import VlanCreate

    vlan_site.get_lan_networks = AsyncMock(return_value=[])
    vlan_site._api.request.side_effect = RequestFailed(-1001, "rejected")
    with pytest.raises(RequestFailed, match="rejected"):
        await vlan_site.create_vlan(VlanCreate("example", 20))
    assert vlan_site._api.request.await_count == 1
    assert vlan_site.get_lan_networks.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("changes", [{"id": ""}, {"primary": True}, {"futureSetting": True}, {"application": False}])
@pytest.mark.parametrize("operation", ["create", "update"])
async def test_vlan_readback_rejects_incomplete_protected_or_drifted_models(vlan_site, changes, operation):
    from tplink_omada_client.exceptions import OmadaClientException
    from tplink_omada_client.vlans import VlanCreate, VlanUpdate

    before = LanNetwork(vlan_site._vlan_fixture["network"])
    after = LanNetwork(before.raw_data | {"name": "renamed"} | changes)
    if operation == "create":
        vlan_site.get_lan_networks = AsyncMock(side_effect=[[], [after]])
        action = vlan_site.create_vlan(VlanCreate("renamed", 3990))
    else:
        vlan_site.get_lan_networks = AsyncMock(side_effect=[[before], [after]])
        action = vlan_site.update_vlan(before.id, VlanUpdate(name="renamed"))
    with pytest.raises(OmadaClientException, match="read-back"):
        await action
    assert vlan_site._api.request.await_count == 1


@pytest.mark.asyncio
async def test_vlan_apply_revalidates_conflicts_after_preview(vlan_site):
    from tplink_omada_client.vlans import VlanCreate

    settings = VlanCreate("example-vlan", 3990)
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[], [LanNetwork(vlan_site._vlan_fixture["network"])]])
    await vlan_site.preview_vlan_create(settings)
    with pytest.raises(ValueError, match="already"):
        await vlan_site.create_vlan(settings)
    vlan_site._api.request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["update", "delete"])
@pytest.mark.parametrize("protected_sibling", [False, True])
async def test_vlan_name_selection_rejects_duplicate_identity_before_writing(vlan_site, operation, protected_sibling):
    from tplink_omada_client.vlans import VlanUpdate

    before = LanNetwork(vlan_site._vlan_fixture["network"])
    sibling = LanNetwork(before.raw_data | {
        "name": "other-network", "vlan": 20, "primary": protected_sibling,
        "purpose": "interface" if protected_sibling else "vlan",
    })
    after = [] if operation == "delete" else [LanNetwork(before.raw_data | {"name": "renamed"})]
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[before, sibling], after])
    with pytest.raises(ValueError, match="ambiguous"):
        if operation == "update":
            await vlan_site.update_vlan(before.name, VlanUpdate(name="renamed"))
        else:
            await vlan_site.delete_vlan(before.name)
    vlan_site._api.request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("protected_sibling", [False, True])
async def test_vlan_create_rejects_duplicate_identity_in_complete_readback(vlan_site, protected_sibling):
    from tplink_omada_client.exceptions import OmadaClientException
    from tplink_omada_client.vlans import VlanCreate

    created = LanNetwork(vlan_site._vlan_fixture["network"])
    sibling = LanNetwork(created.raw_data | {
        "name": "other-network", "vlan": 20, "primary": protected_sibling,
        "purpose": "interface" if protected_sibling else "vlan",
    })
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[], [created, sibling]])
    with pytest.raises(OmadaClientException, match="read-back.*inspect controller state"):
        await vlan_site.create_vlan(VlanCreate("example-vlan", 3990))
    assert vlan_site._api.request.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_vlan_missing_readback_identity_preserves_recovery_guidance(vlan_site, operation):
    from tplink_omada_client.exceptions import OmadaClientException
    from tplink_omada_client.vlans import VlanCreate, VlanUpdate

    before = LanNetwork(vlan_site._vlan_fixture["network"])
    after = {k: v for k, v in before.raw_data.items() if k != "id"}
    after["name"] = "renamed"
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[] if operation == "create" else [before], [LanNetwork(after)]])
    with pytest.raises(OmadaClientException, match="read-back.*inspect controller state"):
        if operation == "create":
            await vlan_site.create_vlan(VlanCreate("renamed", 3990))
        elif operation == "update":
            await vlan_site.update_vlan(before.id, VlanUpdate(name="renamed"))
        else:
            await vlan_site.delete_vlan(before.id)
    assert vlan_site._api.request.await_count == 1


INVALID_VLAN_GUARDS = [
    ("dhcpGuard", {"enable": False, "futureSetting": True}),
    ("dhcpGuard", {"enable": 0}),
    ("dhcpGuard", {"enable": False, "dhcpSvr1": 0}),
    ("dhcpGuard", None),
    ("dhcpv6Guard", {"enable": False, "futureSetting": True}),
    ("dhcpv6Guard", {"enable": 0}),
    ("dhcpv6Guard", {"enable": False, "dhcpv6Svr1": 0}),
    ("dhcpv6Guard", None),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("guard,invalid", INVALID_VLAN_GUARDS)
async def test_vlan_update_rejects_unverified_nested_guard_before_writing(vlan_site, guard, invalid):
    from copy import deepcopy

    from tplink_omada_client.vlans import VlanUpdate

    before = LanNetwork(vlan_site._vlan_fixture["network"] | {guard: deepcopy(invalid)})
    after = LanNetwork(before.raw_data | {"name": "renamed"})
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[before], [after]])
    with pytest.raises(ValueError):
        await vlan_site.update_vlan(before.id, VlanUpdate(name="renamed"))
    vlan_site._api.request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize("guard,invalid", INVALID_VLAN_GUARDS)
async def test_vlan_readback_rejects_unverified_nested_guard(vlan_site, operation, guard, invalid):
    from copy import deepcopy

    from tplink_omada_client.exceptions import OmadaClientException
    from tplink_omada_client.vlans import VlanCreate, VlanUpdate

    before = LanNetwork(vlan_site._vlan_fixture["network"])
    after = LanNetwork(before.raw_data | {"name": "renamed", guard: deepcopy(invalid)})
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[] if operation == "create" else [before], [after]])
    with pytest.raises(OmadaClientException, match="read-back.*inspect controller state"):
        if operation == "create":
            await vlan_site.create_vlan(VlanCreate("renamed", 3990))
        else:
            await vlan_site.update_vlan(before.id, VlanUpdate(name="renamed"))
    assert vlan_site._api.request.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["dhcpL2RelayEnable", "igmpSnoopEnable", "fastLeaveEnable", "mldSnoopEnable"])
async def test_vlan_update_rejects_nonboolean_flag_before_writing(vlan_site, field):
    from tplink_omada_client.vlans import VlanUpdate

    before = LanNetwork(vlan_site._vlan_fixture["network"] | {field: 0})
    after = LanNetwork(before.raw_data | {"name": "renamed"})
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[before], [after]])
    with pytest.raises(ValueError):
        await vlan_site.update_vlan(before.id, VlanUpdate(name="renamed"))
    vlan_site._api.request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["dhcpL2RelayEnable", "igmpSnoopEnable", "fastLeaveEnable", "mldSnoopEnable"])
@pytest.mark.parametrize("operation", ["create", "update"])
async def test_vlan_readback_rejects_nonboolean_flag(vlan_site, field, operation):
    from tplink_omada_client.exceptions import OmadaClientException
    from tplink_omada_client.vlans import VlanCreate, VlanUpdate

    before = LanNetwork(vlan_site._vlan_fixture["network"])
    after = LanNetwork(before.raw_data | {"name": "renamed", field: 0})
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[] if operation == "create" else [before], [after]])
    with pytest.raises(OmadaClientException, match="read-back.*inspect controller state"):
        if operation == "create":
            await vlan_site.create_vlan(VlanCreate("renamed", 3990))
        else:
            await vlan_site.update_vlan(before.id, VlanUpdate(name="renamed"))
    assert vlan_site._api.request.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("guard,server,value,valid", [
    ("dhcpGuard", "dhcpSvr2", None, True),
    ("dhcpGuard", "dhcpSvr2", "192.0.2.54", False),
    ("dhcpv6Guard", "dhcpv6Svr2", None, True),
    ("dhcpv6Guard", "dhcpv6Svr2", "2001:db8::54", False),
])
async def test_vlan_readback_only_allows_null_unrequested_guard_server(vlan_site, guard, server, value, valid):
    from tplink_omada_client.exceptions import OmadaClientException
    from tplink_omada_client.vlans import VlanUpdate

    before = LanNetwork(vlan_site._vlan_fixture["network"])
    after = LanNetwork(before.raw_data | {"name": "renamed", guard: {"enable": False, server: value}})
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[before], [after]])
    if valid:
        assert (await vlan_site.update_vlan(before.id, VlanUpdate(name="renamed"))).name == "renamed"
    else:
        with pytest.raises(OmadaClientException, match="read-back.*inspect controller state"):
            await vlan_site.update_vlan(before.id, VlanUpdate(name="renamed"))
    assert vlan_site._api.request.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["preview", "apply"])
@pytest.mark.parametrize("identity,collides", [(None, True), (None, False), ("", False), ("missing", False)])
async def test_vlan_create_rejects_incomplete_inventory_identity(vlan_site, operation, identity, collides):
    from tplink_omada_client.vlans import VlanCreate

    raw = vlan_site._vlan_fixture["network"] | {"id": identity}
    if identity == "missing":
        del raw["id"]
    if not collides:
        raw.update({"name": "other-network", "vlan": 20})
    created = LanNetwork(vlan_site._vlan_fixture["network"])
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[LanNetwork(raw)], [created]])
    with pytest.raises(ValueError):
        if operation == "preview":
            await vlan_site.preview_vlan_create(VlanCreate("example-vlan", 3990))
        else:
            await vlan_site.create_vlan(VlanCreate("example-vlan", 3990))
    vlan_site._api.request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
@pytest.mark.parametrize("timed_out", [False, True])
async def test_vlan_transport_readback_failure_preserves_recovery_guidance(vlan_site, operation, timed_out):
    from tplink_omada_client.exceptions import ConnectionFailed, OmadaClientException
    from tplink_omada_client.vlans import VlanCreate, VlanUpdate

    before = LanNetwork(vlan_site._vlan_fixture["network"])
    error_type = TimeoutError if timed_out else ConnectionFailed
    failure = error_type("offline read-back failure")
    vlan_site.get_lan_networks = AsyncMock(side_effect=[[] if operation == "create" else [before], failure])
    with pytest.raises(OmadaClientException, match="read-back.*may have succeeded.*inspect controller state.*retry") as caught:
        if operation == "create":
            await vlan_site.create_vlan(VlanCreate("example-vlan", 3990))
        elif operation == "update":
            await vlan_site.update_vlan(before.id, VlanUpdate(name="renamed"))
        else:
            await vlan_site.delete_vlan(before.id)
    assert caught.value.__cause__ is failure
    assert vlan_site._api.request.await_count == 1
    assert vlan_site.get_lan_networks.await_count == 2
