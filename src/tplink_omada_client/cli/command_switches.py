"""Implementation for 'switches' command"""

from argparse import _SubParsersAction

from .config import get_target_config, to_omada_connection
from .util import assert_target_argument

async def command_switches(args) -> int:
    """Executes 'switches' command"""
    controller = assert_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        for switch in await site_client.get_switches():
            print(f"{switch.mac} {switch.ip_address:>15}  {switch.name:20} ", end="")
            for port in switch.ports:
                if port.is_disabled:
                    print("x", end="")
                elif port.port_status.link_status:
                    print("\u2611", end="")
                else:
                    print("\u2610", end="")
                if port.port_status.poe_active:
                    print("\u26a1", end="")
                else:
                    print("  ", end="")
            print()
    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'switches' command"""
    switches_parser = subparsers.add_parser(
        "switches",
        aliases=['s'],
        help="Lists switches managed by Omada Controller")
    switches_parser.set_defaults(func=command_switches)
