"""Implementation for 'client' command"""

from argparse import _SubParsersAction
import datetime
from tplink_omada_client.clients import OmadaWiredClientDetails, OmadaWirelessClientDetails
from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_client_mac, get_target_argument

async def command_client(args) -> int:
    """Executes 'client' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        mac = await get_client_mac(site_client, args['mac'])
        client = await site_client.get_client(mac)
        print(f"Name: {client.name}")
        print(f"MAC: {client.mac}")
        if client.ip:
            print(f"IP: {client.ip}")
        if client.host_name:
            print(f"Hostname: {client.host_name}")
        print(f"Blocked: {client.is_blocked}")
        if client.is_active:
            uptime = str(datetime.timedelta(seconds=float(client.connection_time or 0)))
            print(f"Uptime: {uptime}")
        if isinstance(client, OmadaWiredClientDetails):
            if client.connect_dev_type == 'switch':
                print(f"Switch: {client.switch_name} ({client.switch_mac})")
                print(f"Switch port: {client.port}")
            elif client.connect_dev_type == 'gateway':
                print(f"Gateway: {client.gateway_name} ({client.gateway_mac})")
        elif isinstance(client, OmadaWirelessClientDetails):
            print(f"SSID: {client.ssid}")
            print(f"Access Point: {client.ap_name} ({client.ap_mac})")
        
        dump_raw_data(args, client)
    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'client' command"""
    client_parser = subparsers.add_parser(
        "client",
        help="Shows details of a client known to Omada controller")

    client_parser.add_argument(
        "mac",
        help="The MAC address or name of the client",
    )
    client_parser.add_argument('-d', '--dump', help="Output raw client information",  action='store_true')

    client_parser.set_defaults(func=command_client)
