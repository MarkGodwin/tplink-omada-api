"""Implementation for 'access-points' command"""

from argparse import _SubParsersAction

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_checkbox_char, get_target_argument

async def command_access_points(args) -> int:
    """Executes 'access-points' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        for access_point in await site_client.get_access_points():
            print(f"{access_point.mac} {access_point.ip_address:>15}  {access_point.name:20} ", end="")
            print(f"11ac: {get_checkbox_char(access_point.supports_11ac)}  ", end="")
            print(f"5g: {get_checkbox_char(access_point.supports_5g)}  ", end="")
            print(f"5g2: {get_checkbox_char(access_point.supports_5g2)}  ", end="")
            print(f"6g: {get_checkbox_char(access_point.supports_6g)}  ", end="")
            print(f"mesh: {get_checkbox_char(access_point.supports_mesh)}  ", end="")
            print(f" {access_point.model_display_name:20} ", end="")
            print()
            dump_raw_data(args, access_point)
    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'access-points' command"""
    parser = subparsers.add_parser(
        "access-points",
        aliases=['ap'],
        help="Lists access points managed by Omada Controller")
    parser.set_defaults(func=command_access_points)
    parser.add_argument('-d', '--dump', help="Output raw device information",  action='store_true')
