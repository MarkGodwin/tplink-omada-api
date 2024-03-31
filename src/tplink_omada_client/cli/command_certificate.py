"""Implementation for 'set-certificate' command"""

from argparse import ArgumentParser
import getpass

from .config import get_target_config, to_omada_connection
from .util import get_target_argument


async def command_certificate(args) -> int:
    """Executes 'set-certificate' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    if args["password"]:
        password = args["password"]
    else:
        password = getpass.getpass()

    async with to_omada_connection(config) as client:
        await client.set_certificate(args["cert-file"], password)

    print("Certificate uploaded successfully, and enabled. Please reboot the controller to apply the changes.")
    return 0


def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'set-certificate' command"""
    parser: ArgumentParser = subparsers.add_parser("set-certificate", help="Sets a new certificate for the Omada controller.")
    parser.set_defaults(func=command_certificate)

    parser.add_argument("cert-file", help="The certificate file to upload. Must be in PKCS12 PFX format.")

    parser.add_argument("-p", "--password", help="The password for the certificate", required=False)
