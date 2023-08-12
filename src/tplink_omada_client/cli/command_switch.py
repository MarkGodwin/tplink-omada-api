"""Implementation for 'switch' command"""

from argparse import ArgumentParser

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_device_mac, get_target_argument

async def command_switch(args) -> int:
    """Executes 'switch' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        mac = await get_device_mac(site_client, args['mac'])
        switch = await site_client.get_switch(mac)
        print(f"Name: {switch.name}")
        print(f"Address: {switch.mac} ({switch.ip_address})")
        print(f"Status: {switch.status.name} ({switch.status_category.name})")
        print(f"Ports: {switch.number_of_ports}")
        print(f"Supports PoE: {switch.device_capabilities.supports_poe}")
        if switch.device_capabilities.supports_poe:
            print(f"PoE ports: {switch.device_capabilities.poe_ports}")
        print(f"Model: {switch.model_display_name}")
        print(f"LED Setting: {switch.led_setting.name}")
        switch.status_category
        print(f"Uptime: {switch.display_uptime}")
        if switch.uplink:
            print(f"Uplink switch: {switch.uplink.mac} {switch.uplink.name}")
        if len(switch.downlink) > 0:
            print("Downlink devices:")
            for downlink in switch.downlink:
                print(f"- {downlink.mac} {downlink.name}")

        dump_raw_data(args, switch)

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
        help="The MAC address or name of the switch",
    )
    switch_parser.add_argument('-d', '--dump', help="Output raw device information",  action='store_true')

