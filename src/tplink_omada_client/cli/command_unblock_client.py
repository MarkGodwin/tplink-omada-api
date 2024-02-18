"""Implementation for 'client' command"""

from argparse import _SubParsersAction
from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_client_mac, get_target_argument

async def command_unblock_client(args) -> int:
    """Executes 'unblock-client' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        mac = await get_client_mac(site_client, args['mac'])
        await site_client.unblock_client(mac)
    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'unblock-client' command"""
    unblock_parser = subparsers.add_parser(
        "unblock-client",
        help="Unblocks a client allowing access to the network")

    unblock_parser.add_argument(
        "mac",
        help="The MAC address or name of the client",
    )

    unblock_parser.set_defaults(func=command_unblock_client)
