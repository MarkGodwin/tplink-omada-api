"""Implementation for 'controller_info' command"""

from argparse import ArgumentParser

from .config import get_target_config, to_omada_connection
from .util import get_target_argument


async def command_controller_info(args) -> int:
    """Executes 'controller_info' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    conn = to_omada_connection(config)
    ver = await conn.get_controller_version()  # We can get the version without a login
    print(f"Controller version: {ver}")

    async with conn as client:
        name = await client.get_controller_name()
        print(f"Controller name: {name}")

    return 0


def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'gateway' command"""
    parser: ArgumentParser = subparsers.add_parser("controller_info", help="Gets basic information about the Omada Controller")
    parser.set_defaults(func=command_controller_info)
