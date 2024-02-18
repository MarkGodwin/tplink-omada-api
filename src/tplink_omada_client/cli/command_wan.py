"""Implementation for 'wan' command"""

from argparse import ArgumentError, ArgumentParser

from tplink_omada_client.definitions import GatewayPortMode

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_checkbox_char, get_link_status_char, get_device_mac, get_target_argument

async def command_wan(args) -> int:
    """Executes 'wan' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        mac = args['mac']
        if mac:
            mac = await get_device_mac(site_client, mac)
        gateway = await site_client.get_gateway(mac)

        port = int(args['port'])
        port_status = next((p for p in gateway.port_status if p.port_number == port), None) 
        if not port_status:
            print(f"Port {port} not found")
            return -1
        
        if(port_status.mode != GatewayPortMode.WAN):
            print(f"Port {port} is not in WAN mode")
            return -1

        if(args['connect'] or args['disconnect']):
            if(args['ipv6'] and not port_status.wan_ipv6_enabled):
                print(f"Port {port} is not configured for IPv6")
                return -1
            port_status = await site_client.set_gateway_wan_port_connect_state(port, args['connect'], mac, args['ipv6'])

            print("Ok! Note that the gateway may take a few seconds or more to apply the change.")

        print(f"Port:      {port_status.port_number}")
        print(f"Name:      {port_status.display_name} ({port_status.name})")
        print(f"Link:      {get_link_status_char(port_status.link_status)}")
        print(f"Mode:      {port_status.mode.name}")
        print(f"Ipv4:      {get_checkbox_char(port_status.wan_connected)}", end="")
        if(port_status.wan_connected):
            print(f"    {port_status.wan_ip_address}")
        else:
            print()
        print(f"Ipv4Proto: {port_status.wan_protocol}")
        if(port_status.wan_ipv6_enabled):
            print(f"Ipv6:      {get_checkbox_char(port_status.ipv6_wan_connected)}", end="")
            if(port_status.ipv6_wan_connected):
                print(f"    {port_status.wan_ipv6_address}")
            else:
                print()
        print(f"Online:    {get_checkbox_char(port_status.online_detection)}")
        print(f"Speed:     {port_status.link_speed.name}")
        print(f"Duplex:    {port_status.link_duplex.name}")

        dump_raw_data(args, port_status)

    return 0

def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'wan' command"""
    switch_parser: ArgumentParser = subparsers.add_parser(
        "wan",
        help="Controls the gateway's wan ports"
    )
    switch_parser.set_defaults(func=command_wan)

    switch_parser.add_argument(
        "--mac",
        help="The MAC address of the gateway (optional)",
        required=False
    )
    switch_parser.add_argument(
        "-p", "--port",
        help="The port number of the gateway.",
        required=True
    )
    con_discon_grp = switch_parser.add_mutually_exclusive_group()
    con_discon_grp.add_argument(
        "--connect",
        help="Connect the port to the internet",
        action="store_true"
    )
    con_discon_grp.add_argument(
        "--disconnect",
        help="Connect the port from the internet",
        action="store_true"        
    )
    switch_parser.add_argument("--ipv6", help="Connect/Disconnect IPv6 Wan (defaults to IPv4)", action="store_true")
    switch_parser.add_argument('-d', '--dump', help="Output raw port information",  action='store_true')

