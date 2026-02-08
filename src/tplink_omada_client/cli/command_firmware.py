"""Implementation for 'firmware' command"""

from argparse import ArgumentParser
from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_target_argument


async def command_firmware(args) -> int:
    """Executes 'firmware' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        controller_updates = await client.check_firmware_updates()
        if controller_updates.hardware:
            hardware_update = controller_updates.hardware
            status = "\u2757 UPDATE" if hardware_update.upgrade else "\u2713 UP-TO-DATE"
            print(f"{'Controller':<30} {hardware_update.current_version:<36} {hardware_update.latest_version:<36} {status}")
            if hardware_update.upgrade and hardware_update.release_notes and args["release_notes"]:
                print(f"  Release Notes: {hardware_update.release_notes}")
        else:
            print("No controller firmware updates available.")

        dump_raw_data(args, controller_updates)

        site_client = await client.get_site_client(config.site)
        devices = await site_client.get_devices()

        for device in devices:
            firmware = await site_client.get_firmware_details(device)
            status = "\u2757 UPDATE" if firmware.current_version != firmware.latest_version else "\u2713 UP-TO-DATE"
            print(f"{device.name:<30} {firmware.current_version:<36} {firmware.latest_version:<36} {status}")
            if firmware.current_version != firmware.latest_version and firmware.release_notes and args["release_notes"]:
                print(f"  Release Notes: {firmware.release_notes}")

            dump_raw_data(args, firmware)

    return 0


def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'firmware' command"""
    firmware_parser: ArgumentParser = subparsers.add_parser(
        "firmware", help="Shows firmware information and update availability for all devices"
    )
    firmware_parser.set_defaults(func=command_firmware)

    firmware_parser.add_argument("-d", "--dump", help="Output raw firmware information", action="store_true")
    firmware_parser.add_argument("-rn", "--release-notes", help="Show release notes for firmware updates", action="store_true")
