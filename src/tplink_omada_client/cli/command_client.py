"""Implementation for 'client' command"""

from argparse import _SubParsersAction, ArgumentError
import datetime
from tplink_omada_client.clients import OmadaWiredClientDetails, OmadaWirelessClientDetails
from tplink_omada_client.omadasiteclient import OmadaClientFixedAddress, OmadaClientSettings
from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_client_mac, get_target_argument


async def command_client(args) -> int:
    """Executes 'client' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        mac = await get_client_mac(site_client, args["mac"])

        if args["set_name"] or args["lock_to_ap"] or args["unlock"] or args["fixed_ip"] or args["dynamic_ip"]:
            settings = OmadaClientSettings()
            if args["set_name"]:
                settings.name = args["set_name"]
            if args["lock_to_ap"]:
                settings.lock_to_aps = args["lock_to_ap"]
            if args["unlock"]:
                settings.lock_to_aps = []
            if args["dynamic_ip"]:
                settings.fixed_address = OmadaClientFixedAddress()
            elif args["fixed_ip"]:
                if not args["network"]:
                    raise ArgumentError(args["network"], "Network ID must be specified when reserving an IP address")
                settings.fixed_address = OmadaClientFixedAddress(network_id=args["network"], ip_address=args["fixed_ip"])
            client = await site_client.update_client(mac, settings)
        else:
            client = await site_client.get_client(mac)
        print_client(client)

        dump_raw_data(args, client)
    return 0


def print_client(client):
    """Prints details of a client to the console."""
    print(f"Name: {client.name}")
    print(f"MAC: {client.mac}")
    if client.ip:
        print(f"IP: {client.ip}")
    if client.host_name:
        print(f"Hostname: {client.host_name}")
    print(f"Blocked: {client.is_blocked}")
    if client.is_active:
        uptime = str(datetime.timedelta(seconds=float(client.connection_time or 0)))
        print(f"Uptime: {uptime}")
    if isinstance(client, OmadaWiredClientDetails):
        if client.connect_dev_type == "switch":
            print(f"Switch: {client.switch_name} ({client.switch_mac})")
            print(f"Switch port: {client.port}")
        elif client.connect_dev_type == "gateway":
            print(f"Gateway: {client.gateway_name} ({client.gateway_mac})")
    elif isinstance(client, OmadaWirelessClientDetails):
        print(f"SSID: {client.ssid}")
        print(f"Access Point: {client.ap_name} ({client.ap_mac})")


def list_of_strings(arg):
    """Converts a comma-separated list of strings into a list of strings."""
    return arg.split(",")


def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'client' command"""
    client_parser = subparsers.add_parser("client", help="Shows details of a client known to Omada controller")

    client_parser.add_argument(
        "mac",
        help="The MAC address or name of the client",
    )
    client_parser.add_argument("-sn", "--set-name", help="Set the client's name", metavar="NAME")
    lock_grp = client_parser.add_mutually_exclusive_group()
    lock_grp.add_argument(
        "-l", "--lock-to-ap", help="Lock the client to the specified access point(s)", metavar="MACs", type=list_of_strings
    )
    lock_grp.add_argument("-u", "--unlock", help="Unlock the client", action="store_true")

    fixed_ip_grp = client_parser.add_argument_group("IP Reservation")
    fixed_ip_en_dis_grp = fixed_ip_grp.add_mutually_exclusive_group()
    fixed_ip_en_dis_grp.add_argument("-ip", "--fixed-ip", help="Reserve the client's IP address")
    fixed_ip_en_dis_grp.add_argument("-dyn", "--dynamic-ip", help="Remove the client's IP reservation", action="store_true")
    fixed_ip_grp.add_argument("-n", "--network", help="Network ID for reservation")

    client_parser.add_argument("-d", "--dump", help="Output raw client information", action="store_true")

    client_parser.set_defaults(func=command_client)
