"""Implementation for 'known-clients' command"""

from argparse import _SubParsersAction
from datetime import datetime
from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_target_argument

async def command_known_clients(args) -> int:
    """Executes 'known-clients' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        async for client in site_client.get_known_clients():
            if client.mac == client.name:
                name = ""
            else:
                name = f" {client.name}"
            if client.is_blocked:
                blocked = "blocked"
            else:
                blocked = ""
            lastseen = str(datetime.utcfromtimestamp(client.last_seen))
            print(f"{client.mac}{name:<25}{blocked:<8} {lastseen}")
            dump_raw_data(args, client)

    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'known-clients' command"""
    known_clients_parser = subparsers.add_parser(
        "known-clients",
        help="Lists all clients known to the Omada controller")
    known_clients_parser.add_argument('-d', '--dump', help="Output raw client information",  action='store_true')

    known_clients_parser.set_defaults(func=command_known_clients)
