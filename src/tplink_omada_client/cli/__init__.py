""" Omada CLI """
import argparse
import asyncio
import sys
from typing import Sequence, Union

from tplink_omada_client.exceptions import LoginFailed

from . import (
    command_block_client,
    command_client,
    command_clients,
    command_default,
    command_devices,
    command_known_clients,
    command_gateway,
    command_switch,
    command_switches,
    command_access_points,
    command_access_point,
    command_target,
    command_targets,
    command_switch_ports,
    command_unblock_client,
    command_set_device_led,
    command_set_client_name,
    command_wan,
    command_poe
)

def main(argv: Union[Sequence[str], None] = None) -> int:
    """Entry point for Omada CLI"""
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-t', '--target',
        help="The target Omada controller",
        default=""
    )

    subparsers = parser.add_subparsers(
        title='Available commands',
        metavar='command',
    )

    command_block_client.arg_parser(subparsers)
    command_client.arg_parser(subparsers)
    command_clients.arg_parser(subparsers)
    command_default.arg_parser(subparsers)
    command_devices.arg_parser(subparsers)
    command_gateway.arg_parser(subparsers)
    command_known_clients.arg_parser(subparsers)
    command_switch.arg_parser(subparsers)
    command_switches.arg_parser(subparsers)
    command_access_points.arg_parser(subparsers)
    command_access_point.arg_parser(subparsers)
    command_switch_ports.arg_parser(subparsers)
    command_target.arg_parser(subparsers)
    command_targets.arg_parser(subparsers)
    command_unblock_client.arg_parser(subparsers)
    command_set_device_led.arg_parser(subparsers)
    command_set_client_name.arg_parser(subparsers)
    command_wan.arg_parser(subparsers)
    command_poe.arg_parser(subparsers)

    try:
        args = parser.parse_args(args=argv)
        if "func" in args:
            return asyncio.run(args.func(vars(args)))
        parser.print_help()
        return 1
    except argparse.ArgumentError as error:
        parser.print_usage()
        print(error.message)
        return 1
    except LoginFailed as error:
        print(error)
        return 2
