"""VLAN-only payload validation and preservation against captured fixtures."""

import copy
import json
from pathlib import Path

import pytest

from tplink_omada_client.networks import LanNetwork


@pytest.fixture
def vlan_fixture():
    return json.loads((Path(__file__).parent / "fixtures/vlan_management.json").read_text())


def test_create_matches_captured_range_payload(vlan_fixture):
    from tplink_omada_client.vlans import VlanCreate

    assert VlanCreate("example-vlan", 3990).payload() == vlan_fixture["create"]["payload"]


@pytest.mark.parametrize("vlan_id", [0, 4091, True, 1.5, "30", None])
def test_create_rejects_invalid_ids(vlan_id):
    from tplink_omada_client.vlans import VlanCreate

    with pytest.raises(ValueError, match="VLAN ID"):
        VlanCreate("example", vlan_id)


@pytest.mark.parametrize("name", ["", "  ", "x" * 129, "é" * 65, "a\nb", "a\x1bb", None])
def test_create_rejects_invalid_names(name):
    from tplink_omada_client.vlans import VlanCreate

    with pytest.raises(ValueError, match="name"):
        VlanCreate(name, 30)


def test_create_accepts_boundaries_and_trims_names():
    from tplink_omada_client.vlans import VlanCreate

    assert VlanCreate(" x ", 4090).payload()["name"] == "x"
    assert VlanCreate("x" * 128, 2).payload()["vlans"] == "2"
    with pytest.raises(ValueError, match="protected"):
        VlanCreate("example", 1)


def test_update_preserves_nested_settings_and_does_not_mutate_source(vlan_fixture):
    from tplink_omada_client.vlans import VlanUpdate

    raw = vlan_fixture["network"]
    raw["dhcpGuard"] = {"enable": True, "dhcpSvr1": "192.0.2.53"}
    raw["igmpSnoopEnable"] = True
    original = copy.deepcopy(raw)
    payload = VlanUpdate(name="renamed").payload(LanNetwork(raw))
    assert payload["name"] == "renamed"
    assert payload["vlan"] == 3990
    assert payload["dhcpGuard"] == original["dhcpGuard"]
    assert payload["igmpSnoopEnable"] is True
    assert payload["application"] == 0
    assert payload["fastLeaveEnable"] is False
    assert "id" not in payload and "site" not in payload and "primary" not in payload
    assert "interfaceIds" not in payload and "origName" not in payload
    payload["dhcpGuard"]["enable"] = False
    assert raw == original


@pytest.mark.parametrize("changes", [{"primary": True}, {"vlan": 1}, {"purpose": "interface"}, {"primary": None}, {"application": 1}])
def test_update_protects_default_routed_and_unverified_targets(vlan_fixture, changes):
    from tplink_omada_client.vlans import VlanUpdate

    raw = vlan_fixture["network"] | changes
    with pytest.raises(ValueError):
        VlanUpdate(name="renamed").payload(LanNetwork(raw))


def test_update_rejects_unknown_fields(vlan_fixture):
    from tplink_omada_client.vlans import VlanUpdate

    raw = vlan_fixture["network"] | {"futureSetting": {"enabled": True}}
    with pytest.raises(ValueError, match="Unsupported VLAN fields"):
        VlanUpdate(name="renamed").payload(LanNetwork(raw))


@pytest.mark.parametrize("kwargs", [{}, {"name": ""}, {"vlan_id": 4091}, {"vlan_id": True}, {"vlan_id": 1}])
def test_update_rejects_invalid_changes(kwargs):
    from tplink_omada_client.vlans import VlanUpdate

    with pytest.raises(ValueError):
        VlanUpdate(**kwargs)


def test_conflicts_reject_duplicate_names_and_ids(vlan_fixture):
    from tplink_omada_client.vlans import validate_vlan_conflicts

    networks = [LanNetwork(vlan_fixture["network"])]
    with pytest.raises(ValueError, match="already"):
        validate_vlan_conflicts({"name": "other", "vlan": 3990}, networks)
    with pytest.raises(ValueError, match="already"):
        validate_vlan_conflicts({"name": "EXAMPLE-VLAN", "vlans": "20"}, networks)
    validate_vlan_conflicts({"name": "example-vlan", "vlan": 3990}, networks, exclude_id="example-network-id")


def test_resolve_rejects_missing_ambiguous_and_cross_id_name_matches(vlan_fixture):
    from tplink_omada_client.vlans import resolve_vlan_target

    network = LanNetwork(vlan_fixture["network"])
    assert resolve_vlan_target("example-vlan", [network]).id == network.id
    assert resolve_vlan_target(network.id, [network]).id == network.id
    other = LanNetwork(vlan_fixture["network"] | {"id": "other"})
    cases = [
        ("missing", [network]),
        ("example-vlan", [network, other]),
        (network.id, [network, LanNetwork(other.raw_data | {"name": network.id})]),
    ]
    for target, networks in cases:
        with pytest.raises(ValueError, match="missing or ambiguous"):
            resolve_vlan_target(target, networks)


@pytest.mark.parametrize("name", ["Default", " MANAGEMENT ", "Management(Default)"])
def test_requests_reject_reserved_names_before_creating_unmanageable_targets(name):
    from tplink_omada_client.vlans import VlanCreate, VlanUpdate

    for request in [lambda: VlanCreate(name, 20), lambda: VlanUpdate(name=name)]:
        with pytest.raises(ValueError, match="protected"):
            request()


@pytest.mark.parametrize("network_id", ["", None, "../other", "a/b", "a?x=1", "a#fragment"])
def test_update_refuses_missing_or_unsafe_network_identity(vlan_fixture, network_id):
    from tplink_omada_client.vlans import VlanUpdate

    with pytest.raises(ValueError, match="identity"):
        VlanUpdate(name="renamed").payload(LanNetwork(vlan_fixture["network"] | {"id": network_id}))
