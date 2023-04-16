"""Implementation for 'devices' command"""

from argparse import _SubParsersAction
import json
from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_target_argument

async def command_devices(args) -> int:
    """Executes 'devices' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        for device in await site_client.get_devices():
            print(f"{device.mac} {device.ip_address:>15} {device.type:>7} {device.status_category.name:16} {device.name:20} {device.model_display_name}")
            dump_raw_data(args, device)
    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'devices' command"""
    devices_parser = subparsers.add_parser(
        "devices",
        aliases=['d'],
        help="Lists devices managed by Omada Controller")
    devices_parser.add_argument('-d', '--dump', help="Output raw device information",  action='store_true')

    devices_parser.set_defaults(func=command_devices)
