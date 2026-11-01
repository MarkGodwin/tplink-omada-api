"""Implementation for 'set-certificate' command"""

import getpass
from argparse import ArgumentParser

from .config import get_target_config, to_omada_connection
from .util import get_target_argument


async def command_certificate(args) -> int:
    """Executes 'set-certificate' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    key_file = args.get("key_file")
    cert_type = args.get("format") or ("PEM" if key_file is not None else "PFX")
    password = args["password"]
    if cert_type == "PEM":
        if not key_file:
            raise ValueError("PEM certificates require --key-file")
        if password:
            raise ValueError("PEM requires an unencrypted private key; do not supply --password")
        password = ""
    elif key_file is not None:
        raise ValueError("--key-file can only be used with PEM certificates")
    elif password is None:
        password = getpass.getpass()

    async with to_omada_connection(config) as client:
        await client.set_certificate(args["cert-file"], password, key_file=key_file, cert_type=cert_type)

    print("Certificate uploaded successfully, and enabled. Please reboot the controller to apply the changes.")
    return 0


def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'set-certificate' command"""
    parser: ArgumentParser = subparsers.add_parser("set-certificate", help="Sets a new certificate for the Omada controller.")
    parser.set_defaults(func=command_certificate)

    parser.add_argument(
        "cert-file", help="The certificate file to upload. PFX by default, PEM with --key-file, or JKS with --format JKS."
    )

    parser.add_argument("--key-file", help="Unencrypted PEM private key file (selects PEM format)")
    parser.add_argument(
        "--format", type=str.upper, choices=("PFX", "PEM", "JKS"),
        help="Certificate format (default: PFX, or PEM with --key-file)"
    )

    parser.add_argument("-p", "--password", help="The password for the certificate", required=False)
