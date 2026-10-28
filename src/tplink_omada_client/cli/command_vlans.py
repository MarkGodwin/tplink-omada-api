"""Implementation for the VLAN CLI command group."""

import json
import sys
from argparse import ArgumentParser, _SubParsersAction
from typing import Any

from ..exceptions import OmadaClientException
from ..vlans import VlanCreate, VlanUpdate
from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_target_argument


def _dhcp_status(enabled: bool | None) -> str:
    """Return a readable DHCP state for an optional controller value."""
    if enabled is None:
        return "-"
    return "enabled" if enabled else "disabled"


async def command_vlan_list(args: dict[str, Any]) -> int:
    """List LAN networks."""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        networks = await site_client.get_lan_networks()

        print(f"{'Network ID':<28} {'Name':<24} {'VLAN ID':<8} {'Gateway subnet':<22} {'DHCP':<8}")
        print("-" * 98)
        for network in networks:
            vlan_id = str(network.vlan_id) if network.vlan_id is not None else "-"
            gateway_subnet = network.gateway_subnet or "-"
            print(f"{network.id:<28} {network.name:<24} {vlan_id:<8} {gateway_subnet:<22} {_dhcp_status(network.dhcp_enabled):<8}")
            dump_raw_data(args, network)

    return 0


async def command_vlan_mutation(args: dict[str, Any]) -> int:
    """Preview VLAN-only changes; write only with explicit operator approval."""
    try:
        operation = args["vlan_command"]
        if operation not in {"create", "modify", "delete"}:
            raise ValueError("Unknown VLAN operation")
        create_settings = VlanCreate(args["name"], args["vlan_id"]) if operation == "create" else None
        update_settings = VlanUpdate(name=args.get("name"), vlan_id=args.get("vlan_id")) if operation == "modify" else None
        apply = args.get("apply", False)
        config = get_target_config(get_target_argument(args))
        async with to_omada_connection(config) as client:
            site = await client.get_site_client(config.site)
            if create_settings is not None:
                payload = await site.preview_vlan_create(create_settings)
                print(f"Create VLAN-only network: {create_settings.name} (VLAN {create_settings.vlan_id})")
                print(json.dumps(payload, indent=2, sort_keys=True))
                print("Scope: switches and gateway; existing All/trunk profiles may carry the VLAN. No routing or DHCP is created.")
                if apply:
                    result = await site.create_vlan(create_settings)
                    print(f"Verified create: {result.name} ({result.id}), VLAN {result.vlan_id}")
            elif update_settings is not None:
                network, payload = await site.preview_vlan_update(args["network"], update_settings)
                print(f"Modify VLAN-only network: {network.name} ({network.id})")
                print("Before: " + json.dumps({k: network.raw_data.get(k) for k in payload}, sort_keys=True))
                print("After:  " + json.dumps(payload, sort_keys=True))
                print("Scope: changing a VLAN ID can affect existing trunks, profiles and dependent services.")
                if apply:
                    result = await site.update_vlan(network.id, update_settings, by_id=True)
                    print(f"Verified state: {result.name} ({result.id}), VLAN {result.vlan_id}")
            else:
                network = await site.preview_vlan_delete(args["network"])
                print(f"Delete VLAN-only network: {network.name} ({network.id}), VLAN {network.vlan_id}")
                print(
                    "WARNING: Deletion can disrupt dependent SSIDs, trunks, profiles and policies; "
                    "controller conflict checks are authoritative."
                )
                if apply:
                    await site.delete_vlan(network.id, by_id=True)
                    print(f"Verified delete: {network.name} ({network.id})")
            if not apply:
                print("Preview only; no mutation sent. Use --apply to execute.")
        return 0
    except (ValueError, OmadaClientException) as error:
        print(str(error), file=sys.stderr)
        return 1


def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configure the VLAN command group."""
    parser: ArgumentParser = subparsers.add_parser("vlan", help="List LAN networks or manage VLAN-only networks")
    commands = parser.add_subparsers(dest="vlan_command", required=True)
    list_parser = commands.add_parser("list", help="Lists LAN networks")
    list_parser.add_argument("-d", "--dump", help="Output raw LAN-network information", action="store_true")
    list_parser.set_defaults(func=command_vlan_list)
    create = commands.add_parser("create", help="Preview a VLAN-only create")
    create.add_argument("--name", required=True)
    create.add_argument("--vlan-id", type=int, required=True)
    modify = commands.add_parser("modify", help="Preview a VLAN-only name/ID change")
    modify.add_argument("network", help="Exact network ID or unambiguous exact name")
    modify.add_argument("--name")
    modify.add_argument("--vlan-id", type=int)
    delete = commands.add_parser("delete", help="Preview a non-primary VLAN-only deletion")
    delete.add_argument("network", help="Exact network ID or unambiguous exact name")
    for mutation in (create, modify, delete):
        mutation.add_argument("--apply", action="store_true", help="Apply after fresh validation; default is read-only preview")
        mutation.set_defaults(func=command_vlan_mutation)
