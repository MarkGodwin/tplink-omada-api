"""Implementation for 'switch' command"""

from argparse import ArgumentParser

from .config import get_target_config, to_omada_connection
from .util import assert_target_argument

async def command_switch(args) -> int:
    """Executes 'switch' command"""
    controller = assert_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        switch = await site_client.get_switch(args['mac'])
        print(f"Name: {switch.name}")
        print(f"Address: {switch.mac} ({switch.ip_address})")
        print(f"Ports: {switch.number_of_ports}")
        print(f"Supports PoE: {switch.device_capabilities.supports_poe}")
        if switch.device_capabilities.supports_poe:
            print(f"PoE ports: {switch.device_capabilities.poe_ports}")
        print(f"Model: {switch.model_display_name}")
        switch.status_category
        print(f"Uptime: {switch.display_uptime}")
        if switch.uplink:
            print(f"Uplink switch: {switch.uplink.mac} {switch.uplink.name}")
        if len(switch.downlink) > 0:
            print("Downlink devices:")
            for downlink in switch.downlink:
                print(f"- {downlink.mac} {downlink.name}")

    return 0

def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'switches' command"""
    switch_parser: ArgumentParser = subparsers.add_parser(
        "switch",
        help="Shows details about the specified switch"
    )
    switch_parser.set_defaults(func=command_switch)

    switch_parser.add_argument(
        "mac",
        help="The MAC address of the switch",
    )
