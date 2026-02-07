"""Implementation of 'target' command"""

from argparse import _SubParsersAction, ArgumentError
import getpass
from tplink_omada_client.exceptions import OmadaClientException
from .util import get_target_argument, assert_target_argument
from .config import ControllerConfig, delete_target_config, get_target_config, set_target_config, to_omada_connection


def _update_existing_config(config: ControllerConfig, args: dict) -> None:
    """Updates existing config with provided arguments"""
    if args["url"]:
        config.url = args["url"]
    if args["username"]:
        config.username = args["username"]
    if args["password"]:
        config.password = args["password"]
    if args["site"]:
        config.site = args["site"]
    if args["verify_ssl"]:
        config.verify_ssl = True
    elif args["no_verify_ssl"]:
        config.verify_ssl = False


def _create_new_config(args: dict) -> ControllerConfig:
    """Creates a new controller config from arguments"""
    if not args["url"] or not args["username"]:
        raise ArgumentError(None, "URL and username are required for new targets")

    password = args["password"] if args["password"] else getpass.getpass()
    return ControllerConfig(
        url=args["url"],
        username=args["username"],
        password=password,
        site=args["site"] if args["site"] else "Default",
        verify_ssl=args["verify_ssl"] or not args["no_verify_ssl"],
    )


def _get_or_create_config(target: str, args: dict) -> ControllerConfig:
    """Gets existing config or creates new one"""
    try:
        config = get_target_config(target)
    except ValueError as exc:
        if args["delete"]:
            raise ArgumentError(None, "Specified target does not exist") from exc
        config = _create_new_config(args)
    else:
        _update_existing_config(config, args)
    return config


async def _validate_and_save_config(target: str, config: ControllerConfig, args: dict) -> bool:
    """Validates config by connecting to controller and saves if valid"""
    try:
        async with to_omada_connection(config) as client:
            name = await client.get_controller_name()
            sites = await client.get_sites()
            for site in sites:
                if config.site == site.name:
                    print(f"Set target {target} to controller {name} and site {site.name}")
                    set_target_config(target, config, args["set_default"])
                    return True
            print(f"Count not find site with name '{args['site']}' on the controller.")
            print("Make sure you specify the correct site name with the --site parameter.")
            print("Available sites are:")
            for site in sites:
                print(f"  {site.name}")
            return False
    except OmadaClientException as e:
        print(f"Could not connect to controller with provided credentials: {e}")
        print("Target has not been added.")
        return False


async def command_target(args) -> int:
    """Executes 'target' command"""
    assert_target_argument(args)
    target = get_target_argument(args)

    if args["delete"]:
        delete_target_config(target)
        return 0

    config = _get_or_create_config(target, args)
    await _validate_and_save_config(target, config, args)
    return 0


def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures argument parser for 'target' command"""
    set_parser = subparsers.add_parser(
        "target",
        help="Add Omada Controller to list of targets",
    )

    set_parser.set_defaults(func=command_target)
    add_group = set_parser.add_argument_group(title="Add/Update Targets", description="Specify options to add or update a named target")
    add_group.add_argument(
        "--url",
        help="The URL of the Omada controller",
        required=False,
    )
    add_group.add_argument(
        "--username",
        help="The name of the user used to authenticate",
        required=False,
    )
    add_group.add_argument(
        "--password",
        help="The user's password, password will be prompted if not provided",
    )
    add_group.add_argument("--site", help="The Omada site to control")
    add_group.add_argument("-sd", "--set-default", help="Set this target as the default", action="store_true")
    add_group.add_argument("--verify-ssl", help="Verify the controller's SSL certificate (default on add)", action="store_true")
    add_group.add_argument("--no-verify-ssl", help="Do not verify the controller's SSL certificate", action="store_true")

    set_parser.add_argument("--delete", help="Delete the target", action="store_true")
