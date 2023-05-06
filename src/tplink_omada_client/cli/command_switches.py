"""Implementation for 'switches' command"""

from argparse import _SubParsersAction

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_link_status_char, get_power_char, get_target_argument

async def command_switches(args) -> int:
    """Executes 'switches' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        for switch in await site_client.get_switches():
            print(f"{switch.mac} {switch.ip_address:>15}  {switch.name:20} ", end="")
            for port in switch.ports:
                if port.is_disabled:
                    print("x", end="")
                else:
                    print(get_link_status_char(port.port_status.link_status), end="")
                print(get_power_char(port.port_status.poe_active), end="")

            print()
            dump_raw_data(args, switch)
    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'switches' command"""
    switches_parser = subparsers.add_parser(
        "switches",
        aliases=['s'],
        help="Lists switches managed by Omada Controller")
    switches_parser.set_defaults(func=command_switches)
    switches_parser.add_argument('-d', '--dump', help="Output raw device information",  action='store_true')
