"""Implementation for 'devices' command"""

from argparse import _SubParsersAction

from .config import get_target_config, to_omada_connection
from .util import assert_target_argument

async def command_devices(args) -> int:
    """Executes 'devices' command"""
    controller = assert_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        for device in await site_client.get_devices():
            print(f"{device.mac} {device.ip_address:>15} {device.type:>6}  {device.name:20} {device.model_display_name}")
    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'devices' command"""
    devices_parser = subparsers.add_parser(
        "devices",
        aliases=['d'],
        help="Lists devices managed by Omada Controller")
    devices_parser.set_defaults(func=command_devices)
