# What's this?

A basic Python client for calling the TP-Link Omada controller API.

## Installation

```console
pip install tplink-omada-client
```

Note: Version 1.4 requires Python 3.11.
Note: Version 1.5 and later requires Python 3.13.

## Supported features

Only a subset of the controller's features are supported:
* Automatic Login/Re-login
* Basic controller information
* List sites
* Within site:
    * List Devices (APs, Gateways and Switches)
    * Basic device information
    * Get firmware information and initiating automatic updates
    * Port status and configuraton for Switches
    * Lan port configuration for Access Points
    * Gateway port status and WAN port Connect/Disconnect control
    * IP, IP-port and MAC group inventory and guarded create/modify/delete (source-derived; offline-tested)

Tested with OC200 on Omada Controller Version 5.5.7 - 6.2.x. Other versions may not be fully compatible.
Version 5.0.x is definitely not compatible.

## Controller update checks

`await client.check_firmware_updates()` follows the controller's configured release
channel. Omada 6.3 or later uses `maintenance/software/channelUpdate` directly for
both software and hardware controllers; older versions use
`controller/notification/updateInfo`. On 6.3 or later, you can check a different channel without changing
the controller's configuration or installing an update:

```python
updates = await client.check_firmware_updates(channel=0)  # Release channel
if updates.upgrade:
    print(updates.current_version, updates.latest_version)
    print(updates.release_notes)
```

Software controllers return application versions in `updates.software`. Hardware
controllers such as the OC200 return firmware versions in `updates.hardware`;
their release notes may describe a different controller application version.
An explicitly requested channel that is absent from the response, or channel
selection on a controller older than 6.3, raises `ValueError`.

## CLI

This package provides a simple CLI for interacting with one or more Omada Controllers. To start using the
CLI, you must first target a Controller.

```sh
$ omada -t NAME target --url https://your.omada.controller.here --user admin --password password --site MySite --set-default
```

Where `NAME` is a name of your choosing to identify the targeted controller. `--site` defaults to the Omada
default site name, 'Default'.  If you do not provide a password as an argument, you will be prompted for a
password.

Once you have successfully targeted a controller you can test that things are working by running:

```sh
$ omada devices
```
This will list all the devices being managed by your controller.

### Groups

Inspect and manage IP, IP-port and MAC groups using the existing configured target:

```sh
$ omada -t home group list
$ omada -t home group list --type mac
$ omada -t home group show "Example hosts"
$ omada -t home group show --type ip --id <group-id> --dump
```

List includes group kind, ID, name and writability. `--dump` on list/show is a
diagnostic view, not a stable automation schema or an accepted write payload.
Unknown kinds remain visible in inventory but cannot be written.

Create/modify/delete **preview by default**. Add `--apply` to apply and verify.
There is no mandatory token or preceding command invocation:

```sh
$ omada -t home group create --type ip --name "Example hosts" --subnet 192.0.2.7/32
$ omada -t home group create --type ip --name "Example hosts" --subnet 192.0.2.7/32 --apply
$ omada -t home group create --type ip-port --name HTTPS --subnet 192.0.2.0/24 --port 443
$ omada -t home group create --type mac --name "Example devices" --mac "Phone=02:AA:BB:CC:DD:01"
$ omada -t home group modify "Example hosts" --name "Trusted hosts"
$ omada -t home group modify --type ip --id <group-id> --name "Trusted hosts" --apply
$ omada -t home group delete --type ip --id <group-id>
$ omada -t home group delete --type ip --id <group-id> --apply
```

Selection prefers an exact ID, then a unique exact name; ambiguity fails. An
explicit `--id` requires `--type` and never falls back to a name. Kind is immutable.
Default/protected, malformed and unsupported target configurations fail closed.

Repeated `--subnet`, `--port` and `--mac` options **replace the whole selected
collection**, not append to it. Omitted collections are preserved. To retain
several members, supply all of them. Ports accept single numbers or inclusive
ranges (`--port 80 --port 1000-1010`), within 0..65535. Group names are trimmed
and limited to 64 UTF-16 code units. Supported new/replacement IP collections are
1–16 members for IP groups and 0–8 for IP-port groups; MAC membership and IP-port
port membership cannot be empty. Larger untouched collections are not truncated.

IP-port creation without `--subnet`, or modification with `--clear-subnets`,
means **no IP restriction**. The preview warns that those ports apply to any IP.
`--clear-subnets` is incompatible with `--subnet` and invalid for other kinds.

MAC addresses accept colon/dash notation. `--mac ADDRESS` preserves the alias
of a retained address; `--mac NAME=ADDRESS` changes it, and `--mac =ADDRESS`
explicitly clears it. Names containing `=` split at the final `=`. Retained
addresses keep their actual controller rule IDs; new addresses never borrow
removed members' IDs. Unspecified supported settings and metadata are preserved.

Typed library callers use `GroupProfile` from `tplink_omada_client.networks` and
the immutable requests/identity/member types from `tplink_omada_client.group_models`:

```python
from tplink_omada_client.group_models import GroupIdentity, GroupType, IpGroupUpdate

# site_client is an existing OmadaSiteClient for the intended controller/site.
identity = GroupIdentity(GroupType.IP, "example-group-id")
change = IpGroupUpdate(name="Trusted hosts")
preview = await site_client.preview_group_update(identity, change)
updated = await site_client.update_group(identity, change, expected_data=preview.before)
```

`get_groups`, `preview_group_create/update/delete` and `create_group`,
`update_group`, `delete_group` share the same validated lifecycle as the CLI.
Library mutation methods are explicit writes; the CLI adds the preview/apply gate.
Previews include immutable, non-secret `GroupContext` (controller endpoint/ID and
site ID). `GroupProfile.mac_members` returns read-only `ObservedMacMember` values
with opaque rule IDs and alias/rule presence flags, not editable request members.

Apply re-reads current inventory, binds a stable kind/ID, checks conflicts and
the same-invocation preview preimage, skips no-ops and verifies writes by read-back.
An acknowledgement alone is not success. A preview from a separate invocation
is informational: later apply validates current state, not a saved plan. Preflight
and verification are not atomic; concurrent controller changes can still race.

Group changes can affect existing consumers. Reference discovery is incomplete;
`count` does not establish that a group is unused. Controller dependency errors
are preserved; this feature does not detach consumers, cascade, roll back or add
mutation retries. Shared authentication retains its existing re-login/re-dispatch
behaviour, so this is not an exactly-once guarantee.
The observed UI serializer uses `count || null`: zero/null/absent metadata becomes
null on the wire, positive values are preserved, and raw preimages retain zero.
This specific normalization says nothing about backend reference semantics.

Timeouts, lost acknowledgements, mismatching read-back or interruption after a
possible write require **inspection before retrying**. Failure is nonzero; no
unverified success is printed. `GroupWriteUncertain` preserves the original cause,
safe controller/site context, conservative handoff history, acknowledgement status
and `request` versus `read-back` phase. Handoffs are not proof of delivery.
Cancellation stays `CancelledError` with detached `group_context`, `group_attempts`,
`group_phase`, `group_operation`, `group_identity` and `group_acknowledged` attributes;
only unresolved/acknowledged histories receive an uncertainty note and
`group_recovery`. Definitively rejected-only histories do not. For an uncertain
create, inspect inventory rather than blindly creating again. Group CLI failures
retain existing exit conventions and codes but omit malformed or secret-bearing
response details; original exceptions remain available to library callers.

The group wire contract was researched from an installed 5.15.8.12 frontend and
tested with synthetic offline transports. A separately authorised live smoke test
on that controller also passed inventory/detail, previews, create/modify/delete
and no-op checks for IP, IP-port and MAC groups, including clearing IP-port IP
restrictions and retaining/adding named MAC members. Existing groups were unchanged
and all disposable groups were deleted. This is evidence for that installation,
not a runtime pin, cross-version certification, capacity test or live dependency
rejection test; shared compatibility handling is unchanged.

Read-back accepts integer subnet masks and recognised response-only metadata;
these fields are not forwarded as editable settings. The observed plain IP-port
mode (`portType=0`, empty `portMaskList`) is supported; other port modes/masks and
non-custom resource markers fail closed for writes. A controller-populated count
is accepted only when it matches requested member cardinality on creation, or
tracks a cardinality change from a matching preimage count. Other count drift still
fails verification, and count never proves a group is unused. Other network domains
remain separate capabilities.

### Firmware

Check controller and device firmware, optionally selecting the controller's release channel:

```sh
$ omada firmware
$ omada firmware --channel 0 --release-notes
```

`--channel 0` checks the release channel on Omada 6.3 or later without changing the
controller's configured channel. Omit it to follow the configured channel. This
option applies only to the controller update check; device checks are unchanged.

For a hardware controller such as the OC200, preview the available update:

```sh
$ omada -t OC200 controller-firmware-update --channel 0 --release-notes
```

Add `--apply` to submit the update and restart the controller:

```sh
$ omada -t OC200 controller-firmware-update --channel 0 --apply
```

Each invocation checks the channel again and selects its latest available firmware.
Omit `--channel` to use the configured channel. The command does not change the
configured channel or update managed devices. It rejects software controllers and
updates prohibited by the controller. A successful exit after `--apply` means the
request was accepted; check the controller's web interface for installation progress.

### DHCP

List, create, modify, and delete DHCP reservations:

```sh
$ omada dhcp list
$ omada dhcp create --mac AA:BB:CC:11:22:33 --ip 192.168.1.100 --net-id <network-id> --name "my-device"
$ omada dhcp modify --mac AA:BB:CC:11:22:33 --ip 192.168.1.101
$ omada dhcp delete --mac AA:BB:CC:11:22:33
```

### VLANs

List LAN networks and the DHCP state reported by the controller:

```sh
$ omada vlan list
```

Use the existing port-profile command when inspecting switch VLAN profiles:

```sh
$ omada port-profiles
```

The listing includes the network ID needed by DHCP reservation commands; `--dump` additionally prints the raw model.

VLAN-only lifecycle follows the library's shared controller compatibility handling; it has no additional exact-version requirement. The wire contract was live-tested on controller **5.15.8.12**; this records test provenance, not a compatibility guarantee for every other controller. Routed LAN (`purpose=interface`) targets are rejected. Names accept up to 128 UTF-8 bytes without control characters; VLAN IDs accept 2–4090. VLAN 1 and primary/default/management networks are protected.

```sh
$ omada vlan create --name example-vlan --vlan-id 3990
$ omada vlan modify <network-id-or-exact-name> --name example-vlan-renamed
$ omada vlan delete <network-id-or-exact-name>
```

These commands **preview by default**, using reads for target/conflict validation but sending no mutation. Add `--apply` to execute after fresh validation:

```sh
$ omada vlan create --name example-vlan --vlan-id 3990 --apply
```

Creation uses `application=0` (switches and gateway) without routing or DHCP. Existing All/trunk profiles can carry the new VLAN; no subnet does **not** imply isolation. This command does not explicitly assign SSIDs, switch-port profiles/PVIDs or policies. Review dependencies before changing a VLAN ID or deleting a network; controller conflict checks remain authoritative.

The library provides typed `VlanCreate` and `VlanUpdate` requests in `tplink_omada_client.vlans`, read-only `preview_vlan_create/update/delete` helpers, and `OmadaSiteClient.create_vlan/update_vlan/delete_vlan`. Updates preserve existing writable settings and reject unknown controller fields. No-op updates do not write. Mutations return acknowledgements, so successful create/update results and deletion absence are verified by re-listing.

When applying a previously resolved network ID through the library, pass `by_id=True` to `update_vlan` or `delete_vlan` (also supported by their preview helpers). This fails if that ID disappears instead of treating it as another network's name. The CLI automatically uses this strict identity mode after its initial ID/name selection.

On a read-back failure, inspect the controller before retrying: a write may already have succeeded. There is no automatic write retry or broad cleanup at the lifecycle layer. To reverse an update, explicitly apply the old name/ID; to remove a created test network, preview deletion by its exact ID and explicitly apply it. Do not recreate a deleted network expecting restored IDs or dependencies. Routed LAN, gateway subnet and DHCP mutations remain a separate validation gate.

To see a list of all the available commands, run:

```sh
$ omada -h
```

You can set up multiple targets (controllers and sites), and specify the target with the `-t <NAME>` parameter.
If you don't specify a target, the default will be used, if that has been set.

The CLI is still young so if there is any functionality you need, please create an issue and let us know.

## Future

The available API surface is quite large. More of this could be exposed in the future.
There is an undocumented Websocket API which could potentially be used to get a stream of updates. However,
I'm not sure how fully featured this subscription channel is on the controller. It seems to be rarely used,
so probably doesn't include client connect/disconnect notifications.

The Omada platform is transitioning to a new OpenAPI API which this library will need to switch over to using
eventually. We will try to avoid breaking changes when this happens, but some will be unavoidable - particularly
authentication.

For now, we can use the OpenAPI endpoint with the old authentication style, just like the front-end UI does.
Eventually, we need to switch over to OAuth, but probably once all of the APIs have been migrated.

## Contributing

There is a VS Code development container, which sets up all of the requirements for running the package.

## License

MIT Open Source license.
