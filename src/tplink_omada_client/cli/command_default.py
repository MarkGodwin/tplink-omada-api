"""Implementation of 'default' command"""

from argparse import _SubParsersAction

from .util import assert_target_argument
from .config import set_default_target, get_target_config


async def command_target(args) -> int:
    """Executes 'default' command"""
    target = assert_target_argument(args)
    get_target_config(target)

    set_default_target(target)
    return 0


def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures argument parser for 'default' command"""
    set_parser = subparsers.add_parser(
        "default",
        help="Sets the default target",
    )
    set_parser.set_defaults(func=command_target)
