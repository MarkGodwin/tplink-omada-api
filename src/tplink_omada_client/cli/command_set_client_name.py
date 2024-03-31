"""Implementation for 'set-client-name' command"""

from argparse import _SubParsersAction
from tplink_omada_client.cli.command_client import print_client
from tplink_omada_client.omadasiteclient import OmadaClientSettings
from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_client_mac, get_target_argument


async def command_set_client_name(args) -> int:
    """Executes 'set-client-name' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        mac = await get_client_mac(site_client, args["mac"])

        name = args["name"]
        client = await site_client.update_client(mac, OmadaClientSettings(name=name))

        print_client(client)

        dump_raw_data(args, client)

    return 0


def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'set-client-name' command"""
    parser = subparsers.add_parser("set-client-name", help="Sets the name of an omada client")
    parser.add_argument(
        "mac",
        help="The MAC address or name of the client to set the name for",
    )
    parser.add_argument("name", help="The new name of the client")
    parser.add_argument("-d", "--dump", help="Output raw client information", action="store_true")

    parser.set_defaults(func=command_set_client_name)
