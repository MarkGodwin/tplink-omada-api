"""Implementation for 'clients' command"""

from argparse import _SubParsersAction
from tplink_omada_client.clients import OmadaWiredClient, OmadaWirelessClient
from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_target_argument

async def command_clients(args) -> int:
    """Executes 'clients' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        async for client in site_client.get_connected_clients():
            if client.ip:
                ip = client.ip
            else:
                ip = '-'
            print(f"{client.mac} {ip:15} {(client.name if not None else ''):20} ", end = "")
            if isinstance(client, OmadaWiredClient):
                if client.connect_dev_type == 'switch':
                    print(f"{client.switch_name} ({client.port})")
                elif client.connect_dev_type == 'gateway':
                    print(f"{client.gateway_name}")

            elif isinstance(client, OmadaWirelessClient):
                print(f"{client.ssid} ({client.ap_name})")
            dump_raw_data(args, client)
    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'clients' command"""
    clients_parser = subparsers.add_parser(
        "clients",
        aliases=['c'],
        help="Lists clients connected to site network")
    clients_parser.add_argument('-d', '--dump', help="Output raw client information",  action='store_true')

    clients_parser.set_defaults(func=command_clients)
