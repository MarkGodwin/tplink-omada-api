""" Omada CLI """
import argparse
import asyncio

from .config import ControllerConfig, to_omada_connection, set_controller_config

CONTROLLER_ARG: str = "controller"

async def command_controllers(args):
    """Executes 'controllers' subcommand"""
    print("Controllers: ", args)


async def command_devices(args):
    """Executes 'devices' subcommand"""
    print("Devices: ", args)


async def command_set_controller(args):
    """Executes 'set-controller' subcommand"""
    if CONTROLLER_ARG not in args or args[CONTROLLER_ARG] is None:
        raise argparse.ArgumentError(None, f"error: Missing --{CONTROLLER_ARG} argument")
    controller = args[CONTROLLER_ARG]
    # TODO Prompt if password empty
    config = ControllerConfig(
        url=args['url'],
        username=args['username'],
        password=args['password'],
        site=args['site'],
    )
    # Connect to controller to validate config
    async with to_omada_connection(config) as client:
        await client.get_controller_name()
        # TODO add simple site info API and call to validate site

    set_controller_config(controller, config)


def main():
    """Entry point for Omada CLI"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--controller',
        help="The target Omada controller",
        )

    subparsers = parser.add_subparsers(
        title='Available commands',
        metavar='command',
        dest="command",
        )

    # set-controller
    set_parser = subparsers.add_parser(
        "set-controller",
        help="Set the Omada controller to use",
        )
    set_parser.set_defaults(func=command_set_controller)
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

    # controllers
    controllers_parser = subparsers.add_parser(
        "controllers",
        help="Lists the controllers known to omada")
    controllers_parser.set_defaults(func=command_controllers)

    devices_parser = subparsers.add_parser(
        "devices",
        help="Lists devices known to Omada Controller")
    devices_parser.set_defaults(func=command_devices)

    args = parser.parse_args()
    try:
        asyncio.run(args.func(vars(args)))
    except argparse.ArgumentError as error:
        parser.print_usage()
        print(error.message)


if __name__ == '__main__':
    main()
