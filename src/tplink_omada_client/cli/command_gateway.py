"""Implementation for 'gateway' command"""

from argparse import ArgumentParser

from tplink_omada_client.definitions import GatewayPortMode, LinkStatus

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_link_status_char, get_device_mac, get_target_argument

async def command_gateway(args) -> int:
    """Executes 'gateway' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        mac = args['mac']
        if mac:
            mac = await get_device_mac(site_client, mac)
        gateway = await site_client.get_gateway(mac)
        print(f"Name: {gateway.name}")
        print(f"Address: {gateway.mac} ({gateway.ip_address})")
        print(f"Status: {gateway.status.name} ({gateway.status_category.name})")
        print(f"Ports: {gateway.number_of_ports}")
        print(f"Supports PoE: {gateway.supports_poe}")
        print(f"Model: {gateway.model_display_name}")
        gateway.status_category
        print(f"Uptime: {gateway.display_uptime}")
        wan_ports = (p for p in gateway.port_status if p.mode == GatewayPortMode.WAN)
        lan_ports = (p for p in gateway.port_status if p.mode == GatewayPortMode.LAN)
        print("WAN Ports:")
        for p in wan_ports:
            print(f"    Port: {p.port_number:>2} {p.type.name:7} {p.ip:>15} {p.wan_protocol:>8} ", end="")
            print('\u2611' if p.wan_connected else '\u2610')
        print("LAN Ports:")
        for p in lan_ports:
            print(f"    Port: {p.port_number:>2} {p.type.name:7} {get_link_status_char(p.link_status)}")
        print(f"LED Setting: {gateway.led_setting.name}")

        dump_raw_data(args, gateway)

    return 0

def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'gateway' command"""
    switch_parser: ArgumentParser = subparsers.add_parser(
        "gateway",
        help="Shows details about the site's gateway"
    )
    switch_parser.set_defaults(func=command_gateway)

    switch_parser.add_argument(
        "--mac",
        help="The MAC address of the gateway (optional)",
        required=False
    )
    switch_parser.add_argument('-d', '--dump', help="Output raw device information",  action='store_true')

