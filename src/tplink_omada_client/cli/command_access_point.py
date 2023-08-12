"""Implementation for 'access-point' command"""

from argparse import ArgumentParser

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_checkbox_char, get_device_mac, get_power_char, get_target_argument

async def command_access_point(args) -> int:
    """Executes 'access-point' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        mac = await get_device_mac(site_client, args['mac'])
        access_point = await site_client.get_access_point(mac)
        print(f"Name: {access_point.name}")
        print(f"Address: {access_point.mac} ({access_point.ip_address})")
        print(f"Status: {access_point.status.name} ({access_point.status_category.name})")
        print(f"LAN Ports: {len(access_point.lan_port_settings)}")
        for p in access_point.lan_port_settings:
            print(f"   Port {p.port_name}  PoE Supported: {get_checkbox_char(p.supports_poe)} {get_power_char(p.poe_enable)}  Vlan: {get_checkbox_char(p.supports_vlan and p.local_vlan_enable)} {p.local_vlan_id}")
        print(f"Model: {access_point.model_display_name}")
        print(f"LED Setting: {access_point.led_setting.name}")
        print(f"Uptime: {access_point.display_uptime}")
        print(f"WiFi uplink:  {get_checkbox_char(access_point.wireless_linked)}")
        uplink = access_point.wired_uplink
        if uplink is not None:
            print(f"Uplink switch: {uplink.mac} {uplink.name}")
        else:
            print(f"Uplink switch: <None>")

        print("WiFi Features:")
        print(f"    802.11ag: {get_checkbox_char(access_point.supports_11ac)}")
        print(f"    5G:       {get_checkbox_char(access_point.supports_5g)}")
        print(f"    5G2:      {get_checkbox_char(access_point.supports_5g2)}")
        print(f"    Wifi 6:   {get_checkbox_char(access_point.supports_6g)}")
        print(f"    Mesh:     {get_checkbox_char(access_point.supports_mesh)}")

        dump_raw_data(args, access_point)

    return 0

def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'access-point' command"""
    parser: ArgumentParser = subparsers.add_parser(
        "access-point",
        help="Shows details about the specified access point"
    )
    parser.set_defaults(func=command_access_point)

    parser.add_argument(
        "mac",
        help="The MAC address or name of the access point",
    )
    parser.add_argument('-d', '--dump', help="Output raw device information",  action='store_true')

