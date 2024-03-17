"""Implementation for 'poe' command"""

from argparse import ArgumentError, ArgumentParser

from tplink_omada_client.definitions import OmadaApiData, PoEMode
from tplink_omada_client.devices import OmadaDevice
from tplink_omada_client.omadasiteclient import AccessPointPortSettings, GatewayPortSettings, OmadaSiteClient, SwitchPortOverrides

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_device_by_mac_or_name, get_target_argument

async def set_gateway_poe(site_client: OmadaSiteClient, device: OmadaDevice, port: int, change: bool, on: bool) -> OmadaApiData:
    if change:
        result = await site_client.set_gateway_port_settings(port, GatewayPortSettings(enable_poe=on), device)
    else:
        result = await site_client.get_gateway_port(port, device)
    print(f"Gateway {device.name} Port {port} PoE is {result.poe_mode.name}")
    return result

async def set_switch_poe(site_client: OmadaSiteClient, device: OmadaDevice, port: int, change: bool, on: bool) -> OmadaApiData:
    if change:
        result = await site_client.update_switch_port(device, port, overrides=SwitchPortOverrides(enable_poe=on))
    else:
        result = await site_client.get_switch_port(device, port)
    print(f"Switch {device.name} Port {port} PoE now is {result.poe_mode.name}")
    return result

async def set_access_point_poe(site_client: OmadaSiteClient, device: OmadaDevice, port: int, change: bool, on: bool) -> OmadaApiData:
    if change:
        result = await site_client.update_access_point_port(device, f"ETH{port}", AccessPointPortSettings(enable_poe=on))
    else:
        result = await site_client.get_access_point_port(device, f"ETH{port}")
    print(f"Access point {device.name} Port {result.port_name} PoE is {(PoEMode.ENABLED if result.poe_enable else (PoEMode.DISABLED if result.supports_poe else PoEMode.NONE)).name}")
    return result

async def command_poe(args) -> int:
    """Executes 'poe' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        device = await get_device_by_mac_or_name(site_client, args['mac'])

        port = int(args['port'])
        change = args['on'] or args['off']
        on = bool(args['on'])

        handlers = {"gateway": set_gateway_poe, "switch": set_switch_poe, "ap": set_access_point_poe}
        handler = handlers.get(device.type)
        if not handler:
            raise ArgumentError(args["mac"], "Device type not supported")
        
        result = await handler(site_client, device, port, change, on)
        dump_raw_data(args, result)

    return 0

def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'poe' command"""
    switch_parser: ArgumentParser = subparsers.add_parser(
        "poe",
        help="Controls a device's PoE ports"
    )
    switch_parser.set_defaults(func=command_poe)

    switch_parser.add_argument(
        "mac",
        help="The MAC address or name of the gateway, switch or access point with PoE ports"
    )
    switch_parser.add_argument(
        "-p", "--port",
        help="The port number on the device to set the PoE state.",
        required=True
    )

    con_discon_grp = switch_parser.add_mutually_exclusive_group()
    con_discon_grp.add_argument(
        "--on",
        help="Turn PoE On",
        action="store_true"
    )
    con_discon_grp.add_argument(
        "--off",
        help="Turn PoE Off",
        action="store_true"        
    )
    switch_parser.add_argument('-d', '--dump', help="Output raw port information",  action='store_true')

