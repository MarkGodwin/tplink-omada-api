"""Implementation for 'reboot' command"""

from argparse import ArgumentParser

from .config import get_target_config, to_omada_connection
from .util import get_target_argument


async def command_reboot(args) -> int:
    """Executes 'reboot' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        reboot_time = await client.reboot()

    print(f"Controller is rebooting, and should be back up in approximately {reboot_time} seconds.")
    return 0


def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'gateway' command"""
    parser: ArgumentParser = subparsers.add_parser("reboot", help="Reboot the Omada Controller")
    parser.set_defaults(func=command_reboot)
