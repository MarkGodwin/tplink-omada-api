"""Group lifecycle edge cases exercised through the real offline transport."""

import asyncio
import importlib
from copy import deepcopy
from typing import cast

import pytest
from test_cli_groups import Connection
from test_cli_groups import run as cli_run
from test_group_management import GROUPS, ack, inventory, site
from test_omadaapiconnection import FakeResponse, _login_responses

from tplink_omada_client import cli
from tplink_omada_client.cli.config import ControllerConfig
from tplink_omada_client.exceptions import GroupWriteUncertain
from tplink_omada_client.group_models import GroupContext, GroupIdentity, GroupType, IpGroupUpdate, MacMember
from tplink_omada_client.groups import build_group_update
from tplink_omada_client.networks import GroupProfile

IDENTITY = GroupIdentity(GroupType.IP, "ip-example")


@pytest.mark.parametrize("payload,exit_code", [({"csrfToken": "sensitive-session"}, 1),
    ({"errorCode": -30109, "msg": "echo do-not-print"}, 2),
    ({"errorCode": 42, "msg": "session={'nested': 'sensitive-session'}"}, 1),
    ({"errorCode": 42, "msg": {"privateKey": "sensitive-session"}}, 1)])
def test_group_errors_redact_metadata_and_login_credentials(monkeypatch, capsys, payload, exit_code):
    response = FakeResponse("application/json", payload)
    result, _ = cli_run(monkeypatch, [response, response], ["list"])
    output = capsys.readouterr().out
    assert result == exit_code
    assert "sensitive-session" not in output and "do-not-print" not in output
    assert str(payload.get("errorCode", -30109)) in output


@pytest.mark.parametrize("failure", [TimeoutError("login failed"), asyncio.CancelledError()])
def test_malformed_auth_rejection_retains_unresolved_handoff(failure):
    client, session = site([inventory(GROUPS), FakeResponse("application/json", {
        "errorCode": -30109.0, "msg": "malformed auth code"}), failure])
    expected = asyncio.CancelledError if isinstance(failure, asyncio.CancelledError) else GroupWriteUncertain
    with pytest.raises(expected) as caught:
        asyncio.run(client.delete_group(IDENTITY))
    if isinstance(caught.value, asyncio.CancelledError):
        assert any("inspect" in note for note in getattr(caught.value, "__notes__", ()))
        assert type(caught.value) is asyncio.CancelledError
        assert vars(caught.value)["group_attempts"] == ("unresolved",)
    assert sum(call[0] == "delete" for call in session.calls) == 1


def test_rejected_only_cancellation_has_context_but_no_uncertainty_note():
    client, _ = site([inventory(GROUPS), FakeResponse("application/json", {
        "errorCode": -30109, "msg": "expired"}), asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError) as caught:
        asyncio.run(client.delete_group(IDENTITY))
    error = caught.value
    assert not any("may have succeeded" in note for note in getattr(error, "__notes__", ()))
    assert type(error) is asyncio.CancelledError
    assert vars(error)["group_attempts"] == ("rejected",)
    context = vars(error)["group_context"]
    assert isinstance(context, GroupContext)
    assert context.site_id == "site-example"


@pytest.mark.parametrize("metadata", [{"currentPage": 2}, {"currentPage": 2, "totalRows": 3},
    {"currentPage": True}, {"currentPage": 0}, {"currentPage": "1"},
    {"currentSize": 2}, {"currentSize": True}, {"currentSize": None}, {"hasMore": 0}])
def test_partial_or_malformed_page_metadata_cannot_authorize_writes(metadata):
    response = FakeResponse("application/json", {"errorCode": 0, "result": {"data": GROUPS, **metadata}})
    client, session = site([response, ack(), inventory([])])
    with pytest.raises((ValueError, TypeError)):
        asyncio.run(client.delete_group(IDENTITY))
    assert [call[0] for call in session.calls] == ["get"]


def test_consistent_first_page_metadata_is_accepted():
    response = FakeResponse("application/json", {"errorCode": 0, "result": {
        "data": GROUPS, "currentPage": 1, "currentSize": 100, "totalRows": 3, "hasMore": False}})
    client, _ = site([response, ack(), inventory([])])
    asyncio.run(client.delete_group(IDENTITY))


@pytest.mark.parametrize("count,wire_count", [(None, None), (0, None), (5, 5)])
def test_count_matches_observed_ui_falsy_normalization(count, wire_count):
    before = {**GROUPS[0], "count": count}
    preview = build_group_update(IDENTITY, IpGroupUpdate(name="Renamed"), [GroupProfile(before)])
    assert preview.before is not None and preview.after is not None
    assert preview.before["count"] == count
    assert preview.after["count"] == wire_count
    after = {**before, "name": "Renamed", "count": wire_count}
    client, session = site([inventory([before]), ack(), inventory([after])])
    assert asyncio.run(client.update_group(IDENTITY, IpGroupUpdate(name="Renamed"))).name == "Renamed"
    assert session.calls[1][2]["count"] == wire_count


def test_count_readback_does_not_hide_nonzero_drift():
    before = {**GROUPS[0], "count": 0}
    after = {**before, "name": "Renamed", "count": 7}
    client, _ = site([inventory([before]), ack(), inventory([after])])
    with pytest.raises(GroupWriteUncertain):
        asyncio.run(client.update_group(IDENTITY, IpGroupUpdate(name="Renamed")))


def test_site_preview_has_detached_secret_free_controller_context():
    client, _ = site([inventory(GROUPS)])
    client._api._url = "https://operator:do-not-print@omada.example:8043/private?token=sensitive-session#x"
    preview = asyncio.run(client.preview_group_delete(IDENTITY))
    assert preview.context is not None
    assert preview.context.controller == "https://omada.example:8043"
    assert preview.context.controller_id == "controller-id"
    assert preview.context.site_id == "site-example"
    assert "do-not-print" not in repr(preview.context) and "sensitive-session" not in repr(preview.context)


@pytest.mark.parametrize("phase,attempts", [("request", ("unresolved",)), ("read-back", ("acknowledged",))])
def test_uncertainty_keeps_conservative_phase_and_scope(phase, attempts):
    responses = [inventory(GROUPS)]
    if phase == "read-back":
        responses.append(ack())
    client, _ = site([*responses, TimeoutError("lost")])
    with pytest.raises(GroupWriteUncertain) as caught:
        asyncio.run(client.delete_group(IDENTITY))
    error = caught.value
    assert error.context is not None
    assert error.context.site_id == "site-example" and error.context.controller == "https://omada.example"
    assert error.attempts == attempts and error.phase == phase
    assert error.acknowledged is (phase == "read-back")
    assert error.identity == IDENTITY
    assert "site-example" in str(error) and "handoff" in str(error)


@pytest.mark.parametrize("value", ["80-443-65535", "443-80", "65536", "-1", "", "1.5", True, None])
def test_port_accessor_never_fabricates_ranges(value):
    profile = GroupProfile({**GROUPS[1], "portList": [value]})
    with pytest.raises((ValueError, TypeError)):
        _ = profile.port_members


def test_port_accessor_accepts_valid_boundaries():
    profile = GroupProfile({**GROUPS[1], "portList": ["0", "0-65535", " 443 "]})
    assert [(port.first, port.last) for port in profile.port_members] == [(0, 0), (0, 65535), (443, 443)]


@pytest.mark.parametrize("metadata", [{}, {"name": None, "ruleId": None}, {"name": "Phone", "ruleId": 0}])
def test_observed_mac_member_keeps_opaque_metadata_presence(metadata):
    row = {"macAddress": "02-AA-BB-CC-DD-01", **metadata}
    profile = GroupProfile({**GROUPS[2], "macAddressList": [deepcopy(row)]})
    member = profile.mac_members[0]
    assert member.rule_id == metadata.get("ruleId")
    assert member.rule_id_present is ("ruleId" in metadata)
    assert member.name_present is ("name" in metadata)
    profile.raw_data["macAddressList"][0]["ruleId"] = "changed"
    assert member.rule_id == metadata.get("ruleId")


def test_normal_list_includes_members_and_unrestricted_scope(monkeypatch, capsys):
    result, _ = cli_run(monkeypatch, [inventory(GROUPS)], ["list"])
    output = capsys.readouterr().out
    assert result == 0
    assert "1 subnet" in output and "2 port" in output and "1 MAC" in output
    assert "any IP" in output


def test_default_target_prints_resolved_controller_and_site(monkeypatch, capsys):
    module = importlib.import_module("tplink_omada_client.cli.command_groups")
    client, _ = site([inventory(GROUPS)])
    config = ControllerConfig(
        "https://operator:do-not-print@omada.example?token=sensitive-session",
        "operator", "do-not-print", "Default", True,
    )
    monkeypatch.setattr(module, "get_target_config", lambda _: config)
    monkeypatch.setattr(module, "to_omada_connection", lambda _: Connection(client))
    assert cli.main(["group", "list"]) == 0
    output = capsys.readouterr().out
    assert "omada.example" in output and "site-example" in output and "controller-id" in output
    assert "do-not-print" not in output and "sensitive-session" not in output


@pytest.mark.parametrize("value", ["443", {"port": "443"}, 443])
def test_port_accessor_rejects_non_list_membership(value):
    profile = GroupProfile({**GROUPS[1], "portList": value})
    with pytest.raises((ValueError, TypeError)):
        _ = profile.port_members


@pytest.mark.parametrize("field", ["name", "ruleId"])
@pytest.mark.parametrize("present", [False, True])
def test_retained_mac_readback_preserves_absent_vs_null(field, present):
    before = deepcopy(GROUPS[2])
    row = before["macAddressList"][0]
    if present:
        row[field] = None
    else:
        row.pop(field)
    after = deepcopy(before)
    after["name"] = "Renamed"
    if present:
        after["macAddressList"][0].pop(field)
    else:
        after["macAddressList"][0][field] = None
    client, _ = site([inventory([before]), ack(), inventory([after])])
    from tplink_omada_client.group_models import MacGroupUpdate
    with pytest.raises(GroupWriteUncertain):
        asyncio.run(client.update_group(GroupIdentity(GroupType.MAC, "mac-example"), MacGroupUpdate(name="Renamed")))


def test_observed_rule_ids_cannot_be_supplied_as_write_members():
    from tplink_omada_client.group_models import MacGroupUpdate
    profile = GroupProfile(deepcopy(GROUPS[2]))
    identity = GroupIdentity(GroupType.MAC, "mac-example")
    with pytest.raises((ValueError, TypeError)):
        # Deliberately cross the typed boundary to verify runtime rejection of observed records.
        build_group_update(identity, MacGroupUpdate(members=cast(tuple[MacMember, ...], profile.mac_members)), [profile])


def test_malformed_kind_and_name_cannot_leak_nested_private_data(monkeypatch, capsys):
    row = {**GROUPS[0], "type": {"csrfToken": "sensitive-session"}, "name": {"session": "sensitive-session"}}
    result, _ = cli_run(monkeypatch, [inventory([row])], ["list", "--dump"])
    assert result == 0
    output = capsys.readouterr().out
    assert "sensitive-session" not in output and "[redacted]" in output


def test_preview_summarizes_changed_and_preserved_fields(monkeypatch, capsys):
    result, _ = cli_run(monkeypatch, [inventory(GROUPS)], ["modify", "ip-example", "--name", "Renamed"])
    output = capsys.readouterr().out
    assert result == 0 and "Changed fields: name" in output
    assert "Preserved fields:" in output and "ipList" in output


def test_malformed_auth_then_later_rejection_keeps_unresolved_history():
    client, session = site([inventory(GROUPS), FakeResponse("application/json", {
        "errorCode": -30109.0, "msg": "malformed"}), *_login_responses(),
        FakeResponse("application/json", {"errorCode": 42, "msg": "rejected"})])
    with pytest.raises(GroupWriteUncertain) as caught:
        asyncio.run(client.delete_group(IDENTITY))
    assert caught.value.attempts == ("unresolved", "rejected")
    assert sum(call[0] == "delete" for call in session.calls) == 2


def test_real_overlapping_operations_do_not_share_observation():
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        class WaitingFailure(FakeResponse):
            async def __aenter__(self):
                entered.set()
                await release.wait()
                raise TimeoutError("lost first request")

        client, session = site([inventory(GROUPS), WaitingFailure("application/json"),
                                inventory(GROUPS), ack(), inventory([GROUPS[0]])])
        first = asyncio.create_task(client.delete_group(IDENTITY))
        await asyncio.wait_for(entered.wait(), 5)
        try:
            second = await client.delete_group(GroupIdentity(GroupType.MAC, "mac-example"))
            assert second is None and not first.done()
        finally:
            release.set()
        with pytest.raises(GroupWriteUncertain) as caught:
            await first
        assert caught.value.identity == IDENTITY and caught.value.attempts == ("unresolved",)
        assert sum(call[0] == "delete" for call in session.calls) == 2

    asyncio.run(scenario())


def test_expired_auth_after_preflight_never_claims_mutation_dispatch():
    class ExpiringInventory(FakeResponse):
        async def __aexit__(self, *args):
            client._api._last_logon = 0

    response = ExpiringInventory("application/json", {"errorCode": 0, "result": {"data": GROUPS}})
    client, session = site([response, TimeoutError("status lost"), TimeoutError("login failed")])
    with pytest.raises(TimeoutError, match="login failed"):
        asyncio.run(client.delete_group(IDENTITY))
    assert all(call[0] == "get" for call in session.calls)


@pytest.mark.parametrize("phase", ["request", "read-back"])
def test_real_task_cancellation_retains_structured_recovery(phase):
    async def scenario():
        entered = asyncio.Event()

        class WaitingResponse(FakeResponse):
            async def __aenter__(self) -> FakeResponse:
                entered.set()
                await asyncio.Event().wait()
                return self

        responses = [inventory(GROUPS)]
        if phase == "read-back":
            responses.append(ack())
        client, _ = site([*responses, WaitingResponse("application/json")])
        task = asyncio.create_task(client.delete_group(IDENTITY))
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError) as caught:
            await task
        assert task.cancelled()
        error = caught.value
        assert type(error) is asyncio.CancelledError
        assert vars(error)["group_phase"] == phase
        context = vars(error)["group_context"]
        assert isinstance(context, GroupContext) and context.site_id == "site-example"
        assert vars(error)["group_acknowledged"] is (phase == "read-back")
        assert any("inspect" in note for note in caught.value.__notes__)

    asyncio.run(scenario())


@pytest.mark.parametrize("scheme", ["http", "https", "HTTPS", "hTtPs"])
def test_error_url_strips_userinfo_path_query_and_fragment(monkeypatch, capsys, scheme):
    response = FakeResponse("application/json", {"errorCode": 42,
        "msg": f"Cannot connect to {scheme}://other:alphaZeta@omada.example/route?k=nonpublic#fragment"})
    result, session = cli_run(monkeypatch, [response], ["list"])
    output = capsys.readouterr().out
    assert result == 1 and "Cannot connect" in output and "42" in output
    assert "omada.example" in output
    assert all(value not in output for value in ("other:", "alphaZeta", "/route", "nonpublic", "#fragment"))
    assert [call[0] for call in session.calls] == ["get"]


@pytest.mark.parametrize("code", [
    {"csrfToken": "opaque-code-data"}, [{"cookie": "opaque-code-data"}], "opaque-code-data",
    42.0, True, None,
], ids=["object", "list", "string", "float", "boolean", "null"])
def test_malformed_error_codes_never_render_response_data(monkeypatch, capsys, code):
    response = FakeResponse("application/json", {"errorCode": code, "msg": "bad code"})
    result, session = cli_run(monkeypatch, [response], ["list"])
    output = capsys.readouterr().out
    assert result == 1 and "request failed" in output
    assert "opaque-code-data" not in output and "csrfToken" not in output and "cookie" not in output
    assert "unknown" in output and "response details omitted" in output
    assert [call[0] for call in session.calls] == ["get"]


@pytest.mark.parametrize("code", [42, -1001])
def test_valid_rejection_keeps_useful_message_and_numeric_code(monkeypatch, capsys, code):
    response = FakeResponse("application/json", {"errorCode": code, "msg": "Group is in use"})
    result, session = cli_run(monkeypatch, [response], ["list"])
    output = capsys.readouterr().out
    assert result == 1 and "Group is in use" in output and f"({code})" in output
    assert "unknown" not in output and "response details omitted" not in output
    assert [call[0] for call in session.calls] == ["get"]
