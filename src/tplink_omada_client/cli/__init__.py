""" Omada CLI """
import argparse
import asyncio
import sys
from typing import Any, Sequence, Union

from tplink_omada_client.exceptions import LoginFailed

from . import (
    command_devices,
    command_switch,
    command_switches,
    command_target,
    command_targets,
)

def main(argv: Union[Sequence[str], None] = None) -> int:
    """Entry point for Omada CLI"""
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-t', '--target',
        help="The target Omada controller",
    )

    subparsers = parser.add_subparsers(
        title='Available commands',
        metavar='command',
    )

    command_devices.arg_parser(subparsers)
    command_switch.arg_parser(subparsers)
    command_switches.arg_parser(subparsers)
    command_target.arg_parser(subparsers)
    command_targets.arg_parser(subparsers)

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
