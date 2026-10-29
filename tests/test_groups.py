"""Pure group contracts: preserve policy and identity, not UI row positions."""

import importlib
from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from tplink_omada_client.networks import GroupProfile


def _modules():
    return (importlib.import_module("tplink_omada_client.group_models"),
            importlib.import_module("tplink_omada_client.groups"))


def raw_group(kind=0, identifier: object = "g1", name="Example"):
    return {"groupId": identifier, "name": name, "type": kind, "count": 2,
            "ipList": [{"ip": "192.0.2.7", "mask": "32"}] if kind != 2 else None,
            "portList": ["80", "100-110"] if kind == 1 else None,
            "macAddressList": [{"name": "phone", "macAddress": "02-AA-BB-CC-DD-01", "ruleId": "r1"}] if kind == 2 else None}


def _create(m, kind, name="Example"):
    if kind == 0:
        return m.IpGroupCreate(name, (m.IpSubnet("192.0.2.7", 32),))
    if kind == 1:
        return m.IpPortGroupCreate(name, (), (m.PortRange(80, 80),))
    return m.MacGroupCreate(name, (m.MacMember("02:aa:bb:cc:dd:01"),))


@pytest.mark.parametrize("kind", [0, 1, 2])
def test_create_uses_only_observed_fields(kind):
    m, g = _modules()
    preview = g.build_group_create(_create(m, kind), [])
    assert preview.identity is None
    assert preview.after == {
        "id": None, "name": "Example", "type": kind, "count": None,
        "ipList": [{"ip": "192.0.2.7", "mask": "32"}] if kind == 0 else ([] if kind == 1 else None),
        "portList": ["80"] if kind == 1 else None,
        "macAddressList": [{"name": None, "macAddress": "02-AA-BB-CC-DD-01"}] if kind == 2 else None,
    }
    assert bool(preview.warnings)


@pytest.mark.parametrize("name", ["", "  ", "x" * 65, "\U0001f600" * 33, "bad\nname", "\ud800"])
def test_invalid_group_names_fail_before_payload(name):
    m, g = _modules()
    with pytest.raises(ValueError):
        g.build_group_create(_create(m, 0, name), [])


def test_utf16_name_boundary_and_immutable_request_snapshot():
    m, g = _modules()
    members = [m.IpSubnet("192.0.2.7", 32)]
    request = m.IpGroupCreate(" " + "\U0001f600" * 32 + " ", members)
    members.clear()
    preview = g.build_group_create(request, [])
    assert preview.after["name"] == "\U0001f600" * 32
    assert preview.after["ipList"] == [{"ip": "192.0.2.7", "mask": "32"}]
    with pytest.raises(FrozenInstanceError):
        request.name = "changed"


@pytest.mark.parametrize("address,prefix", [("::1", 32), ("300.1.1.1", 24), ("192.0.2.1", -1),
                                            ("192.0.2.1", 33), ("192.0.2.1", True)])
def test_invalid_ipv4_members_rejected(address, prefix):
    m, g = _modules()
    with pytest.raises(ValueError):
        g.build_group_create(m.IpGroupCreate("Example", (m.IpSubnet(address, prefix),)), [])


@pytest.mark.parametrize("low,high", [(-1, 1), (1, 65536), (90, 80), (True, 80)])
def test_invalid_port_ranges_rejected(low, high):
    m, g = _modules()
    with pytest.raises(ValueError):
        g.build_group_create(m.IpPortGroupCreate("Example", (), (m.PortRange(low, high),)), [])


@pytest.mark.parametrize("kind,count,valid", [(0, 0, False), (0, 16, True), (0, 17, False),
                                             (1, 0, True), (1, 8, True), (1, 9, False)])
def test_supported_ip_membership_bounds(kind, count, valid):
    m, g = _modules()
    members = tuple(m.IpSubnet(f"192.0.2.{i + 1}", 32) for i in range(count))
    request = m.IpGroupCreate("Example", members) if kind == 0 else m.IpPortGroupCreate("Example", members, (m.PortRange(0, 65535),))
    if valid:
        assert len(g.build_group_create(request, []).after["ipList"]) == count
    else:
        with pytest.raises(ValueError):
            g.build_group_create(request, [])


def test_mac_replacement_preserves_retained_alias_and_rule_not_array_position():
    m, g = _modules()
    original = raw_group(2)
    original["macAddressList"].append({"macAddress": "02-AA-BB-CC-DD-02", "name": "remove", "ruleId": "r2"})
    inventory = [GroupProfile(original)]
    request = m.MacGroupUpdate(members=(m.MacMember("02:aa:bb:cc:dd:03"), m.MacMember("02:aa:bb:cc:dd:01")))
    result = g.build_group_update(m.GroupIdentity(m.GroupType.MAC, "g1"), request, inventory)
    assert result.after["macAddressList"] == [
        {"name": None, "macAddress": "02-AA-BB-CC-DD-03"},
        {"name": "phone", "macAddress": "02-AA-BB-CC-DD-01", "ruleId": "r1"},
    ]
    original["macAddressList"].clear()
    assert len(result.before["macAddressList"]) == 2
    assert result.after["macAddressList"][1]["ruleId"] == "r1"


def test_mac_alias_can_be_cleared_and_duplicates_fail():
    m, g = _modules()
    identity = m.GroupIdentity(m.GroupType.MAC, "g1")
    inventory = [GroupProfile(raw_group(2))]
    preview = g.build_group_update(identity, m.MacGroupUpdate(members=(m.MacMember("02:aa:bb:cc:dd:01", ""),)), inventory)
    assert preview.after["macAddressList"][0]["name"] == ""
    with pytest.raises(ValueError):
        g.build_group_create(m.MacGroupCreate("Example", (m.MacMember("02:aa:bb:cc:dd:01"), m.MacMember("02-AA-BB-CC-DD-01"))), [])


@pytest.mark.parametrize("kind", [0, 1, 2])
def test_name_only_preserves_metadata_and_noop(kind):
    m, g = _modules()
    raw = raw_group(kind)
    original = deepcopy(raw)
    cls = (m.IpGroupUpdate, m.IpPortGroupUpdate, m.MacGroupUpdate)[kind]
    identity = m.GroupIdentity(m.GroupType(kind), "g1")
    preview = g.build_group_update(identity, cls(name="Renamed"), [GroupProfile(raw)])
    assert preview.after["count"] == 2
    assert preview.after["id"] == "g1"
    for key in ("ipList", "portList", "macAddressList"):
        assert preview.after[key] == original[key]
    assert raw == original
    assert g.build_group_update(identity, cls(name="Example"), [GroupProfile(raw)]).no_op


@pytest.mark.parametrize("bad_id", [None, "", "../x", "a/b", "a?b", "a%2Fb", True])
def test_bad_identity_is_not_writable(bad_id):
    m, g = _modules()
    with pytest.raises(ValueError):
        g.build_group_create(_create(m, 0), [GroupProfile(raw_group(identifier=bad_id, name="Other"))])


def test_id_precedence_and_no_id_to_name_fallback_on_apply():
    m, g = _modules()
    inventory = [GroupProfile(raw_group(identifier="real", name="same")), GroupProfile(raw_group(identifier="other", name="real"))]
    assert g.resolve_group_target("real", inventory).id == "real"
    with pytest.raises(ValueError):
        g.resolve_group_target("real", inventory[1:], by_id=True)
    with pytest.raises(ValueError):
        g.build_group_delete(m.GroupIdentity(m.GroupType.IP, "real"), inventory[1:])


def test_conflicts_include_other_kinds_and_null_ids():
    m, g = _modules()
    with pytest.raises(ValueError):
        g.build_group_create(_create(m, 0), [GroupProfile(raw_group(2, identifier=None))])


@pytest.mark.parametrize("create", [True, False])
def test_protected_first_member_is_rejected_for_create_and_update(create):
    m, g = _modules()
    subnets = (m.IpSubnet("0.0.0.0", 0),)
    with pytest.raises(ValueError):
        if create:
            g.build_group_create(m.IpGroupCreate("Example", subnets), [])
        else:
            g.build_group_update(m.GroupIdentity(m.GroupType.IP, "g1"), m.IpGroupUpdate(subnets=subnets), [GroupProfile(raw_group())])


def test_nonfirst_zero_address_is_not_globally_banned():
    m, g = _modules()
    preview = g.build_group_create(m.IpGroupCreate("Example", (m.IpSubnet("192.0.2.7", 32), m.IpSubnet("0.0.0.0", 0))), [])
    assert preview.after["ipList"][1] == {"ip": "0.0.0.0", "mask": "0"}


@pytest.mark.parametrize("change", [
    {"future": True}, {"count": True}, {"portList": ["22"]},
    {"ipList": [{"ip": "192.0.2.7", "mask": "32", "future": 1}]},
])
def test_unsupported_existing_target_is_not_silently_rewritten(change):
    m, g = _modules()
    raw = raw_group()
    raw.update(change)
    with pytest.raises(ValueError):
        g.build_group_update(m.GroupIdentity(m.GroupType.IP, "g1"), m.IpGroupUpdate(name="Renamed"), [GroupProfile(raw)])


def test_unknown_kind_is_inspectable_but_not_selected_for_mutation():
    _m, g = _modules()
    unknown = GroupProfile(raw_group(9))
    assert unknown.group_type == 9
    assert unknown.raw_data["name"] == "Example"
    with pytest.raises(ValueError):
        g.resolve_group_target("g1", [unknown])


@pytest.mark.parametrize("case", [0, 1, 2, 3])
def test_create_cannot_omit_required_membership(case):
    m, g = _modules()
    requests = [m.IpGroupCreate("New", None), m.IpPortGroupCreate("New", None, (m.PortRange(80, 80),)),
                m.IpPortGroupCreate("New", (), None), m.MacGroupCreate("New", None)]
    with pytest.raises(ValueError, match="membership"):
        g.build_group_create(requests[case], [])


def test_existing_large_ip_collection_is_preserved_when_not_replaced():
    m, g = _modules()
    raw = raw_group()
    raw["ipList"] = [{"ip": f"192.0.2.{i}", "mask": "32"} for i in range(1, 18)]
    preview = g.build_group_update(m.GroupIdentity(m.GroupType.IP, "g1"), m.IpGroupUpdate(name="Renamed"), [GroupProfile(raw)])
    assert preview.after["ipList"] == raw["ipList"]


@pytest.mark.parametrize("rule", [True, [], {}, "", -1])
def test_unsupported_rule_identity_is_not_reused(rule):
    m, g = _modules()
    raw = raw_group(2)
    raw["macAddressList"][0]["ruleId"] = rule
    with pytest.raises(ValueError):
        g.build_group_update(m.GroupIdentity(m.GroupType.MAC, "g1"), m.MacGroupUpdate(name="Renamed"), [GroupProfile(raw)])
