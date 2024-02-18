"""Implementation for 'set-device-led' command"""

from argparse import _SubParsersAction

from tplink_omada_client.definitions import LedSetting
from .config import get_target_config, to_omada_connection
from .util import get_device_by_mac_or_name, get_target_argument

async def command_set_device_led(args) -> int:
    """Executes 'set-device-led' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        device = await get_device_by_mac_or_name(site_client, args['mac'])
        setting = LedSetting[args['mode']]
        await site_client.set_led_setting(device, setting)
    return 0

def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'set-device-led' command"""
    parser = subparsers.add_parser(
        "set-device-led",
        help="Sets the LED mode of an omada device")
    parser.add_argument(
        "mac",
        help="The MAC address or name of the device to set the LED mode of",
    )
    parser.add_argument("mode", help="The LED mode to set (ON|OFF|SITE_SETTINGS)")

    parser.set_defaults(func=command_set_device_led)
