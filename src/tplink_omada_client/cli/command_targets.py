"""Implementation of 'targets' command"""
from argparse import _SubParsersAction

from .config import (
    get_targets,
)

async def command_targets(args) -> int: # pylint: disable=unused-argument
    """Executes 'targets' command"""
    controllers = get_targets()
    for (controller, config, is_default) in controllers:
        print(f"{('*' if is_default else' ')} {controller:15} {config.url:30} Site: {config.site:15} Username: {config.username}  Verify SSL: {config.verify_ssl}")
    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures argument parser for 'targets' command"""
    # targets
    controllers_parser = subparsers.add_parser(
        "targets",
        aliases=['t'],
        help="Lists the configured targets")
    controllers_parser.set_defaults(func=command_targets)
