"""Controller response metadata and verified group read-back contracts."""

import asyncio
from copy import deepcopy

import pytest
from test_group_management import GROUPS, ack, inventory, site

from tplink_omada_client.exceptions import GroupWriteUncertain
from tplink_omada_client.group_models import (
    GroupIdentity,
    GroupType,
    IpGroupCreate,
    IpPortGroupCreate,
    IpPortGroupUpdate,
    IpSubnet,
    MacGroupCreate,
    MacGroupUpdate,
    MacMember,
    PortRange,
)
from tplink_omada_client.groups import group_payload
from tplink_omada_client.networks import GroupProfile


def observed(row):
    row = deepcopy(row)
    row.update(site="site-example", resource=0)
    for member in row.get("ipList") or []:
        member["mask"] = int(member["mask"])
    row["count"] = sum(len(row.get(key) or []) for key in ("ipList", "portList", "macAddressList"))
    return row


@pytest.mark.parametrize("index", [0, 1, 2])
def test_read_metadata_is_not_forwarded_into_group_payload(index):
    row = observed(GROUPS[index])
    payload = group_payload(GroupProfile(row))
    assert "site" not in payload and "resource" not in payload
    assert payload["count"] == row["count"]
    assert all(isinstance(member["mask"], str) for member in payload["ipList"] or [])
    assert row == observed(GROUPS[index])


@pytest.mark.parametrize("mask", [True, 1.5, -1, 33, None])
def test_integer_response_masks_still_reject_malformed_values(mask):
    row = deepcopy(GROUPS[0])
    row["ipList"][0]["mask"] = mask
    with pytest.raises((ValueError, TypeError)):
        group_payload(GroupProfile(row))


@pytest.mark.parametrize("resource", [True, "0", 1, 2, {}, []])
def test_non_custom_resource_markers_cannot_authorize_writes(resource):
    row = {**GROUPS[0], "resource": resource}
    with pytest.raises((ValueError, TypeError)):
        group_payload(GroupProfile(row))


def test_inventory_rejects_an_explicit_foreign_site():
    row = {**GROUPS[0], "site": "other-site"}
    client, session = site([inventory([row]), ack()])
    with pytest.raises(ValueError):
        asyncio.run(client.get_groups())
    assert [call[0] for call in session.calls] == ["get"]


@pytest.mark.parametrize("index,group_request", [
    (0, IpGroupCreate("New", (IpSubnet("192.0.2.7", 32),))),
    (1, IpPortGroupCreate("New", (), (PortRange(80, 80), PortRange(443, 443)))),
    (2, MacGroupCreate("New", (MacMember("02-AA-BB-CC-DD-01", "Example device"),))),
])
def test_create_verifies_server_populated_member_count(index, group_request):
    row = observed(GROUPS[index])
    row.update(groupId="new-group", name="New")
    client, session = site([inventory([]), ack(), inventory([row])])
    result = asyncio.run(client.create_group(group_request))
    assert result.id == "new-group"
    assert session.calls[1][2]["count"] is None
    assert result.raw_data["count"] == row["count"]


@pytest.mark.parametrize("index,group_request,change", [
    (1, IpPortGroupUpdate(subnets=()), lambda row: row.update(ipList=[], count=2)),
    (2, MacGroupUpdate(members=(MacMember("02-AA-BB-CC-DD-01"), MacMember("02-AA-BB-CC-DD-02", "Second"))),
     lambda row: (row["macAddressList"].append(
         {"macAddress": "02-AA-BB-CC-DD-02", "name": "Second", "ruleId": "new-rule"}), row.update(count=2))),
])
def test_membership_change_verifies_observed_cardinality_metadata(index, group_request, change):
    before = observed(GROUPS[index])
    if index == 1:
        before.update(ipList=[{"ip": "198.51.100.7", "mask": 32}], count=3)
    after = deepcopy(before)
    change(after)
    client, session = site([inventory([before]), ack(), inventory([after])])
    result = asyncio.run(client.update_group(GroupIdentity(GroupType(index), before["groupId"]), group_request))
    assert result.raw_data["count"] == after["count"]
    assert session.calls[1][2]["count"] == before["count"]


@pytest.mark.parametrize("actual_count", [2, 7])
def test_create_rejects_a_non_matching_server_member_count(actual_count):
    row = observed(GROUPS[0])
    row.update(name="New", groupId="new-group", count=actual_count)
    client, _ = site([inventory([]), ack(), inventory([row])])
    with pytest.raises(GroupWriteUncertain):
        asyncio.run(client.create_group(IpGroupCreate("New", (IpSubnet("192.0.2.7", 32),))))


def test_neutral_ip_port_response_metadata_is_not_forwarded():
    row = {**observed(GROUPS[1]), "portType": 0, "portMaskList": []}
    payload = group_payload(GroupProfile(row))
    assert "portType" not in payload and "portMaskList" not in payload
    assert payload["portList"] == ["80", "443"]


@pytest.mark.parametrize("extra", [
    {"portType": True}, {"portType": "0"}, {"portType": 1}, {"portType": -1},
    {"portMaskList": ["443"]}, {"portMaskList": {}},
])
def test_unrepresented_port_modes_cannot_authorize_writes(extra):
    row = {**observed(GROUPS[1]), **extra}
    client, session = site([inventory([row]), ack()])
    with pytest.raises((ValueError, TypeError)):
        asyncio.run(client.update_group(GroupIdentity(GroupType.IP_PORT, row["groupId"]), IpPortGroupUpdate(name="Renamed")))
    assert [call[0] for call in session.calls] == ["get"]
