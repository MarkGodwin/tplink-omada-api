"""Implementation of 'target' command"""
from argparse import _SubParsersAction, ArgumentError
import getpass
import json

from .util import get_target_argument
from .config import ControllerConfig, set_target_config, to_omada_connection

async def command_target(args) -> int:
    """Executes 'target' command"""
    target = get_target_argument(args)

    if args['password']:
        password = args['password']
    else:
        password = getpass.getpass()
    config = ControllerConfig(
        url=args['url'],
        username=args['username'],
        password=password,
        site=args['site'],
    )
    
    # Connect to controller to validate config
    async with to_omada_connection(config) as client:
        name = await client.get_controller_name()
        for site in await client.get_sites():
            if args['site'] == site.name:
                print(f"Set target {target} to controller {name} and site {site.name}")
                set_target_config(target, config, args['set_default'])

    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures argument parser for 'target' command"""
    set_parser = subparsers.add_parser(
        "target",
        help="Add Omada Controller to list of targets",
    )
    set_parser.set_defaults(func=command_target)
    set_parser.add_argument(
        '--url',
        help="The URL of the Omada controller",
        required=True,
    )
    set_parser.add_argument(
        '--username',
        help="The name of the user used to authenticate",
        required=True,
    )
    set_parser.add_argument(
        '--password',
        help="The user's password, password will be prompted if not provided",
    )
    set_parser.add_argument(
        '--site',
        help="The Omada site to user",
        default = "Default",
    )
    set_parser.add_argument(
        '-sd',
        '--set-default',
        help="Set this target as the default",
        action='store_true')

