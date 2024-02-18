"""Implementation for 'switch_ports' command"""

from argparse import ArgumentParser
from typing import List

from tplink_omada_client.definitions import PoEMode, PortType
from tplink_omada_client.devices import OmadaSwitch, OmadaSwitchPortDetails

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_checkbox_char, get_display_bytes, get_link_status_char, get_device_mac, get_power_char, get_target_argument

async def command_switch_ports(args) -> int:
    """Executes 'switch_ports' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        mac = await get_device_mac(site_client, args['mac'])
        switch = await site_client.get_switch(mac)
        ports = await site_client.get_switch_ports(mac)

        filter_port = args['port']
        if filter_port:
            ports = list((p for p in ports if p.port == int(filter_port)))

        if args['table']:
            print_port_table(switch, ports)

        else:
            for p in ports:
                print(f"Port: {p.port:2} - {p.name}")
                print(f"    Type:        {p.type}")
                print(f"    Profile:     {p.profile_name} - {get_checkbox_char(p.has_profile_override)}")
                print(f"    Enabled:     {get_checkbox_char(not p.is_disabled)}")
                print(f"    Status:      {get_link_status_char(p.port_status.link_status)} ")
                if switch.device_capabilities.supports_poe and p.type != PortType.SFP:
                    print(f"    PoE:         {get_checkbox_char(p.poe_mode == PoEMode.ENABLED)} {get_power_char(p.port_status.poe_active)} {p.port_status.poe_power}W ")
                else:
                    print("    PoE:          Not supported")
                print(f"    Link Speed:  {p.port_status.link_speed.name} (Max: {p.max_speed.name})")
                print(f"    Transmitted: {get_display_bytes(p.port_status.bytes_tx)}")
                print(f"    Received:    {get_display_bytes(p.port_status.bytes_rx)}")
                print(f"    Operation:   {p.operation}")
                print(f"    Limit Mode:  {p.bandwidth_limit_mode.name}")

                dump_raw_data(args, p)

    return 0

def print_port_table(switch: OmadaSwitch, ports: List[OmadaSwitchPortDetails]):
    print("No. Name            Profile Ena Ovr Link     Speed PoE  Power      Received  Transmitted")
    for p in ports:
        print(f"{p.port:2}  {p.name[:12]:12} {p.profile_name[:10]:>10}  {get_checkbox_char(not p.is_disabled)}   {get_checkbox_char(p.has_profile_override)}   {get_link_status_char(p.port_status.link_status)}  ", end="")
        if p.port_status.link_status:
            print(f"{p.port_status.link_speed.name[6:]:>10} ", end="")
        else:
            print(f"       --- ", end="")

        if switch.device_capabilities.supports_poe and p.type != PortType.SFP:
            print(f" {get_checkbox_char(p.poe_mode == PoEMode.ENABLED)}{get_power_char(p.port_status.poe_active)} {p.port_status.poe_power:>4}W ", end="")
        else:
            print(" x      -W ", end="")
        print(f" {get_display_bytes(p.port_status.bytes_rx):>12} {get_display_bytes(p.port_status.bytes_tx):>12}")

def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'switch_ports' command"""
    switch_ports_parser: ArgumentParser = subparsers.add_parser(
        "switch_ports",
        help="Shows detailed information about the ports on the specified switch"
    )
    switch_ports_parser.set_defaults(func=command_switch_ports)

    switch_ports_parser.add_argument(
        "mac",
        help="The MAC address or name of the switch",
    )
    switch_ports_parser.add_argument('-d', '--dump', help="Output raw device information",  action='store_true')
    switch_ports_parser.add_argument('-t', '--table', help="Show data in a compact table", action='store_true')
    switch_ports_parser.add_argument('-p', '--port', help="Port number to show information about", default=None)
