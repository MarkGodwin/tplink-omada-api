"""Implementation for 'controller-info' command"""

from argparse import ArgumentParser
from typing import Any

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_target_argument


def _format_value(value: Any) -> str:
    """Format optional controller info values for CLI output."""
    if value is None:
        return "Unknown"
    return str(value)


async def command_controller_info(args) -> int:
    """Executes 'controller-info' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    conn = to_omada_connection(config)
    info = await conn.get_controller_info()  # We can get controller info without a login
    print(f"Controller version: {info.controller_version}")
    print(f"API version: {_format_value(info.api_version)}")
    print(f"Controller ID: {info.omadac_id}")
    print(f"Controller type: {_format_value(info.type)}")
    print(f"Controller category: {_format_value(info.omadac_category)}")
    print(f"Configured: {_format_value(info.configured)}")
    print(f"Root registered: {_format_value(info.registered_root)}")
    print(f"Supports Omada app: {_format_value(info.support_app)}")
    print(f"MSP mode: {_format_value(info.msp_mode)}")
    print(f"Omada cloud URL: {_format_value(info.omada_cloud_url)}")
    dump_raw_data(args, info)

    async with conn as client:
        name = await client.get_controller_name()
        print(f"Controller name: {name}")

    return 0


def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'gateway' command"""
    parser: ArgumentParser = subparsers.add_parser("controller-info", help="Gets basic information about the Omada Controller")
    parser.set_defaults(func=command_controller_info)
    parser.add_argument("-d", "--dump", help="Output raw controller information", action="store_true")
