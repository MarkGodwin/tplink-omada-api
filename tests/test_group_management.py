"""Group lifecycle through the actual authenticated transport, without network access."""

import asyncio
import importlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_omadaapiconnection import FakeResponse, ScriptedSession, _connection, _login_responses

from tplink_omada_client.exceptions import RequestFailed
from tplink_omada_client.omadasiteclient import OmadaSiteClient

GROUPS = json.loads((Path(__file__).parent / "fixtures/group_management.json").read_text())


def inventory(rows):
    return FakeResponse("application/json", {"errorCode": 0, "result": {"data": deepcopy(rows)}})


def ack():
    return FakeResponse("application/json", {"errorCode": 0})


class Session(ScriptedSession):
    def __init__(self, responses):
        super().__init__(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, deepcopy(kwargs.get("json"))))
        return super().request(method, url, **kwargs)


def site(responses):
    session = Session(responses)
    return OmadaSiteClient("site-example", _connection(session)), session


def models():
    return importlib.import_module("tplink_omada_client.group_models")


def update(m, kind, name="Renamed"):
    return (m.IpGroupUpdate, m.IpPortGroupUpdate, m.MacGroupUpdate)[kind](name=name)


@pytest.mark.parametrize("kind", [0, 1, 2])
def test_preview_uses_get_only_and_detaches_preimage(kind):
    m = models()
    client, session = site([inventory(GROUPS)])
    original = deepcopy(GROUPS[kind])
    preview = asyncio.run(client.preview_group_update(m.GroupIdentity(m.GroupType(kind), original["groupId"]), update(m, kind)))
    assert preview.after is not None
    assert preview.after["name"] == "Renamed"
    assert preview.before == original
    assert [call[0] for call in session.calls] == ["get"]


@pytest.mark.parametrize("kind", [0, 1, 2])
def test_update_uses_bound_route_preserves_fields_and_verifies(kind):
    m = models()
    before = deepcopy(GROUPS[kind])
    after = deepcopy(before)
    after["name"] = "Renamed"
    client, session = site([inventory(GROUPS), ack(), inventory([after])])
    result = asyncio.run(client.update_group(m.GroupIdentity(m.GroupType(kind), before["groupId"]), update(m, kind)))
    assert result.name == "Renamed"
    assert [call[0] for call in session.calls] == ["get", "patch", "get"]
    _method, url, body = session.calls[1]
    assert url.endswith(f"/setting/profiles/groups/{kind}/{before['groupId']}")
    assert body["id"] == before["groupId"]
    assert "groupId" not in body
    for field in ("ipList", "portList", "macAddressList", "count"):
        assert body[field] == before[field]


@pytest.mark.parametrize("kind", [0, 1, 2])
def test_create_requires_unique_new_identity_and_verifies(kind):
    m = models()
    if kind == 0:
        request = m.IpGroupCreate("New", (m.IpSubnet("192.0.2.7", 32),))
        row = {**GROUPS[0], "groupId": "new-id", "name": "New"}
    elif kind == 1:
        request = m.IpPortGroupCreate("New", (), (m.PortRange(80, 80), m.PortRange(443, 443)))
        row = {**GROUPS[1], "groupId": "new-id", "name": "New"}
    else:
        request = m.MacGroupCreate("New", (m.MacMember("02-AA-BB-CC-DD-01", "Example device"),))
        row = {**GROUPS[2], "groupId": "new-id", "name": "New"}
    client, session = site([inventory(GROUPS), ack(), inventory([*GROUPS, row])])
    result = asyncio.run(client.create_group(request))
    assert result.id == "new-id"
    assert session.calls[1][0] == "post"
    assert session.calls[1][1].endswith("/setting/profiles/groups")
    assert session.calls[1][2]["id"] is None
    if kind == 2:
        assert "ruleId" not in session.calls[1][2]["macAddressList"][0]
        assert result.raw_data["macAddressList"][0]["ruleId"] == "example-rule"


@pytest.mark.parametrize("kind", [0, 1, 2])
def test_delete_is_bodyless_and_requires_absence(kind):
    m = models()
    identity = m.GroupIdentity(m.GroupType(kind), GROUPS[kind]["groupId"])
    client, session = site([inventory(GROUPS), ack(), inventory([])])
    assert asyncio.run(client.delete_group(identity)) is None
    expected_url = f"https://omada.example/controller-id/api/v2/sites/site-example/setting/profiles/groups/{kind}/{identity.id}"
    assert session.calls[1] == ("delete", expected_url, None)


def test_noop_does_not_dispatch_but_stale_noop_fails():
    m = models()
    identity = m.GroupIdentity(m.GroupType.IP, "ip-example")
    client, session = site([inventory(GROUPS)])
    assert asyncio.run(client.update_group(identity, m.IpGroupUpdate(name="Example hosts"))).id == identity.id
    assert len(session.calls) == 1
    changed = deepcopy(GROUPS)
    changed[0]["count"] = 3
    client, session = site([inventory(changed)])
    with pytest.raises(ValueError, match="changed|stale"):
        asyncio.run(client.update_group(identity, m.IpGroupUpdate(name="Example hosts"), expected_data=GROUPS[0]))
    assert len(session.calls) == 1


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
@pytest.mark.parametrize("failure", [TimeoutError("lost"), ValueError("invalid JSON"), RuntimeError("response stream failed")])
def test_write_failure_is_uncertain_and_never_retried(operation, failure):
    m = models()
    client, session = site([inventory(GROUPS), failure])
    uncertain = importlib.import_module("tplink_omada_client.exceptions").GroupWriteUncertain
    with pytest.raises(uncertain, match="may have succeeded.*inspect") as caught:
        asyncio.run(_operate(client, m, operation))
    assert caught.value.__cause__ is failure
    assert len(session.calls) == 2


def _operate(client, m, operation):
    if operation == "create":
        return client.create_group(m.IpGroupCreate("New", (m.IpSubnet("192.0.2.8", 32),)))
    identity = m.GroupIdentity(m.GroupType.IP, "ip-example")
    if operation == "update":
        return client.update_group(identity, m.IpGroupUpdate(name="New"))
    return client.delete_group(identity)


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_readback_timeout_is_uncertain_not_success(operation):
    m = models()
    client, session = site([inventory(GROUPS), ack(), TimeoutError("read-back")])
    uncertain = importlib.import_module("tplink_omada_client.exceptions").GroupWriteUncertain
    with pytest.raises(uncertain, match="may have succeeded.*inspect"):
        asyncio.run(_operate(client, m, operation))
    assert len(session.calls) == 3


def test_auth_timeout_before_mutation_is_not_uncertain():
    m = models()
    client, session = site([inventory(GROUPS), TimeoutError("login")])

    async def scenario():
        preview = await client.preview_group_update(m.GroupIdentity(m.GroupType.IP, "ip-example"), m.IpGroupUpdate(name="New"))
        assert preview.identity is not None
        client._api._csrf_token = None
        with pytest.raises(TimeoutError, match="login"):
            await client.update_group(preview.identity, m.IpGroupUpdate(name="New"), expected_data=preview.before)
    asyncio.run(scenario())
    assert not any(call[0] in ("patch", "delete") for call in session.calls)


def test_explicit_rejection_preserves_controller_exception():
    m = models()
    client, session = site([inventory(GROUPS), FakeResponse("application/json", {"errorCode": 42, "msg": "in use"})])
    with pytest.raises(RequestFailed, match="in use.*42"):
        asyncio.run(_operate(client, m, "delete"))
    assert len(session.calls) == 2


@pytest.mark.parametrize("rows", [[], [GROUPS[0], GROUPS[0]], [{**GROUPS[0], "groupId": None}]])
def test_update_missing_duplicate_or_malformed_identity_cannot_write(rows):
    m = models()
    client, session = site([inventory(rows)])
    with pytest.raises(ValueError):
        asyncio.run(_operate(client, m, "update"))
    assert len(session.calls) == 1


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_cancelled_mutation_stays_cancelled_and_records_uncertainty(operation):
    m = models()
    client, session = site([inventory(GROUPS), asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError) as caught:
        asyncio.run(_operate(client, m, operation))
    assert any("may have succeeded" in note for note in caught.value.__notes__)
    assert len(session.calls) == 2


def test_relogin_rejection_after_unknown_first_attempt_is_uncertain():
    m = models()
    responses = [inventory(GROUPS), FakeResponse("text/html"), *_login_responses(),
                 FakeResponse("application/json", {"errorCode": 42, "msg": "in use"})]
    client, session = site(responses)
    uncertain = importlib.import_module("tplink_omada_client.exceptions").GroupWriteUncertain
    with pytest.raises(uncertain):
        asyncio.run(_operate(client, m, "delete"))
    assert sum(call[0] == "delete" for call in session.calls) == 2


@pytest.mark.parametrize("operation", ["invalid", "update"])
def test_invalid_private_preview_cannot_mutate_collection(operation):
    m = models()
    client, session = site([ack(), inventory([])])
    preview = m.GroupPreview(operation, None, None, {})
    with pytest.raises(ValueError):
        asyncio.run(client._apply_group(preview, []))
    assert not session.calls


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
@pytest.mark.parametrize("rows", [[{**GROUPS[0], "groupId": None}], [GROUPS[0], GROUPS[0]]])
def test_malformed_readback_is_uncertain(operation, rows):
    m = models()
    client, session = site([inventory(GROUPS), ack(), inventory(rows)])
    uncertain = importlib.import_module("tplink_omada_client.exceptions").GroupWriteUncertain
    with pytest.raises(uncertain):
        asyncio.run(_operate(client, m, operation))
    assert sum(call[0] in ("post", "patch", "delete") for call in session.calls) == 1


def test_retained_mac_rule_drift_is_not_verified():
    m = models()
    changed = deepcopy(GROUPS[2])
    changed["name"] = "Renamed"
    changed["macAddressList"][0]["ruleId"] = "foreign-rule"
    client, _session = site([inventory(GROUPS), ack(), inventory([changed])])
    uncertain = importlib.import_module("tplink_omada_client.exceptions").GroupWriteUncertain
    with pytest.raises(uncertain):
        asyncio.run(client.update_group(m.GroupIdentity(m.GroupType.MAC, "mac-example"), m.MacGroupUpdate(name="Renamed")))


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
@pytest.mark.parametrize("kind", [0, 1, 2])
def test_every_preview_kind_and_operation_is_read_only(operation, kind):
    m = models()
    client, session = site([inventory(GROUPS)])
    identity = m.GroupIdentity(m.GroupType(kind), GROUPS[kind]["groupId"])
    if operation == "create":
        requests = [m.IpGroupCreate("New", (m.IpSubnet("192.0.2.8", 32),)),
                    m.IpPortGroupCreate("New", (), (m.PortRange(80, 80),)),
                    m.MacGroupCreate("New", (m.MacMember("02-AA-BB-CC-DD-02"),))]
        task = client.preview_group_create(requests[kind])
    elif operation == "update":
        task = client.preview_group_update(identity, update(m, kind))
    else:
        task = client.preview_group_delete(identity)
    preview = asyncio.run(task)
    assert preview.operation == operation
    assert [call[0] for call in session.calls] == ["get"]


@pytest.mark.parametrize("phase", ["preflight", "relogin", "readback"])
def test_cancellation_at_each_shared_phase_propagates(phase):
    m = models()
    if phase == "preflight":
        responses = [asyncio.CancelledError()]
    elif phase == "relogin":
        responses = [inventory(GROUPS), FakeResponse("text/html"), asyncio.CancelledError()]
    else:
        responses = [inventory(GROUPS), ack(), asyncio.CancelledError()]
    client, session = site(responses)
    with pytest.raises(asyncio.CancelledError) as caught:
        asyncio.run(_operate(client, m, "delete"))
    notes = getattr(caught.value, "__notes__", ())
    assert bool(notes) is (phase != "preflight")
    assert sum(call[0] == "delete" for call in session.calls) == (0 if phase == "preflight" else 1)


@pytest.mark.parametrize("payload,status", [({"errorCode": 0}, 500), ({"msg": "missing ack"}, 200),
                                            (["bad"], 200), ({"errorCode": False}, 200)])
def test_http_or_malformed_ack_is_not_definitive_rejection(payload, status):
    m = models()
    response = FakeResponse("application/json", payload)
    response.status = status
    client, session = site([inventory(GROUPS), response])
    uncertain = importlib.import_module("tplink_omada_client.exceptions").GroupWriteUncertain
    with pytest.raises(uncertain):
        asyncio.run(_operate(client, m, "delete"))
    assert len(session.calls) == 2


@pytest.mark.parametrize("version", ["5.1.0", "5.9.9", "5.15.8.12", "6.0.0", "6.2.0.0"])
def test_simulated_versions_keep_shared_login_and_group_routes(version):
    m = models()
    login = _login_responses()
    login[0] = FakeResponse("application/json", {"errorCode": 0, "result": {"controllerVer": version, "omadacId": "controller-id"}})
    client, session = site([*login, inventory(GROUPS), ack(), inventory([])])
    client._api._csrf_token = None
    asyncio.run(client.delete_group(m.GroupIdentity(m.GroupType.IP, "ip-example")))
    writes = [call for call in session.calls if call[0] == "delete"]
    assert len(writes) == 1 and writes[0][1].endswith("setting/profiles/groups/0/ip-example")


@pytest.mark.parametrize("result", [{"data": GROUPS, "totalRows": 9}, {"data": GROUPS, "totalRows": True},
                                    {"data": GROUPS, "hasMore": True}, {"data": None}])
def test_incomplete_inventory_cannot_trigger_mutation(result):
    m = models()
    response = FakeResponse("application/json", {"errorCode": 0, "result": result})
    client, session = site([response])
    with pytest.raises((ValueError, TypeError)):
        asyncio.run(_operate(client, m, "delete"))
    assert len(session.calls) == 1


def test_unknown_readback_failure_keeps_ambiguous_success_guidance():
    m = models()
    failure = RuntimeError("response stream failed")
    client, _session = site([inventory(GROUPS), ack(), failure])
    uncertain = importlib.import_module("tplink_omada_client.exceptions").GroupWriteUncertain
    with pytest.raises(uncertain) as caught:
        asyncio.run(_operate(client, m, "delete"))
    assert caught.value.__cause__ is failure
