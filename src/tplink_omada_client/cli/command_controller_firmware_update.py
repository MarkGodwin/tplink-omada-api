"""Preview or start a hardware controller firmware update."""

from argparse import ArgumentParser

from tplink_omada_client.exceptions import OmadaClientException

from .config import get_target_config, to_omada_connection
from .util import get_target_argument


async def command_controller_firmware_update(args) -> int:
    """Check the selected channel before optionally submitting its firmware update."""
    config = get_target_config(get_target_argument(args))
    try:
        async with to_omada_connection(config) as client:
            if (await client.get_controller_type()).is_soft_controller:
                print("Firmware installation is supported only for hardware controllers.")
                return 1

            info = await client.check_firmware_updates(channel=args.get("channel"))
            firmware = info.hardware
            if firmware is None:
                print("The controller did not report hardware firmware update information.")
                return 1
            if firmware.raw_data.get("denyUpgrade"):
                print("The controller currently prohibits this firmware upgrade.")
                return 1
            if not firmware.upgrade:
                print("No controller firmware update is available on the selected channel.")
                return 0

            version = firmware.latest_version
            if not isinstance(version, str) or not version.strip() or version == firmware.current_version:
                print("The controller did not report a usable target firmware version.")
                return 1

            print(f"Controller firmware: {firmware.current_version or 'unknown'} -> {version}")
            if args.get("release_notes") and firmware.release_notes:
                print(f"Release notes: {firmware.release_notes}")
            if not args.get("apply"):
                print("Preview only. Add --apply to install this update; the controller will restart.")
                return 0

            if not await client.install_controller_firmware(version):
                print("The firmware update was not accepted.")
                return 1
    except (ValueError, OmadaClientException) as error:
        print(f"Controller firmware update request failed: {error}")
        return 1

    print("Firmware update request accepted. The controller will restart; check its web interface for progress.")
    return 0


def arg_parser(subparsers) -> None:
    """Register the dedicated controller firmware update command."""
    parser: ArgumentParser = subparsers.add_parser(
        "controller-firmware-update", help="Preview or install an available hardware controller firmware update",
    )
    parser.set_defaults(func=command_controller_firmware_update)
    parser.add_argument(
        "--channel", type=int, metavar="ID",
        help="Controller release channel ID (0 for release; Omada 6.3+). Defaults to the configured channel.",
    )
    parser.add_argument("--release-notes", action="store_true", help="Show the selected update's release notes")
    parser.add_argument("--apply", action="store_true", help="Install the selected update and restart the controller")
