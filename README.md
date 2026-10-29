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

### Configuration files

New configurations are stored in `$XDG_CONFIG_HOME/omada/config.ini`, or
`~/.config/omada/config.ini` when `XDG_CONFIG_HOME` is unset, empty or not an
absolute path. An existing XDG file takes precedence. Otherwise, an existing
`~/.omada.cfg` continues to be read and updated in place. Files are not merged
or automatically migrated. An unreadable or malformed selected file produces
an error rather than falling back to another file.

New application directories are private (`0700`); saved configuration files
use `0600`. Existing parent-directory permissions are left unchanged. Saves
replace the selected file only after the complete new contents have been
written; a failed save keeps the previous file. User-managed file symlinks
remain intact.

Enter passwords literally at the prompt; percent signs need no special escaping.
The stored INI format retains doubled percent signs (`%%`) for compatibility
with existing files/readers. If editing the INI manually, write each password
percent as `%%`. Password placeholders such as `%(username)s` are not expanded
into other configuration values. Configuration files contain credentials in
plain text; keep them private and out of version control.

Once you have successfully targeted a controller you can test that things are working by running:

```sh
$ omada devices
```
This will list all the devices being managed by your controller.

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
