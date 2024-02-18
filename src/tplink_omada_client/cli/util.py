"""Common functionality for multiple commands"""
import argparse
import json

from typing import Any
from re import IGNORECASE, match
from tplink_omada_client.devices import OmadaApiData, OmadaDevice
from tplink_omada_client.definitions import LinkStatus
from tplink_omada_client import OmadaSiteClient

TARGET_ARG: str = "target"

def assert_target_argument(args: dict[str, Any]) -> str:
    """Throws ArgumentError if target arg missing"""
    if args[TARGET_ARG] == "": # The default is now empty
        raise argparse.ArgumentError(None, f"error: Target name must be supplied using --{TARGET_ARG} argument")
    return args[TARGET_ARG]

def get_target_argument(args: dict[str, Any]) -> str:
    return args[TARGET_ARG]

async def get_client_mac(site_client: OmadaSiteClient, mac_or_name: str) -> str:
    if match('([0-9A-F]{2}[-]){5}[0-9A-F]{2}$',
        string=mac_or_name,
        flags=IGNORECASE):
        return mac_or_name

    async for client in site_client.get_known_clients():
        if client.name == mac_or_name:
            return client.mac
    raise argparse.ArgumentError(None, f"Client with name {mac_or_name} not found")

async def get_device_mac(site_client: OmadaSiteClient, mac_or_name: str) -> str:
    if match('([0-9A-F]{2}[-]){5}[0-9A-F]{2}$',
        string=mac_or_name,
        flags=IGNORECASE):
        return mac_or_name

    device = next((d for d in await site_client.get_devices() if d.name == mac_or_name), None)
    if not device:
        raise argparse.ArgumentError(None, f"Device with name {mac_or_name} not found")
    return device.mac

async def get_device_by_mac_or_name(site_client: OmadaSiteClient, mac_or_name: str) -> OmadaDevice:
    device = next((d for d in await site_client.get_devices() if d.name == mac_or_name or d.mac == mac_or_name), None)
    if not device:
        raise argparse.ArgumentError(None, f"Device with name {mac_or_name} not found")
    return device


def dump_raw_data(args: dict[str, Any], data: OmadaApiData):
    if args['dump']:
        print("--- BEGIN RAW DATA ---")
        print(json.dumps(data.raw_data, indent=2,ensure_ascii=False))
        print("---  END RAW DATA  ---")

def get_checkbox_char(checked: bool) -> str:
    """ Returns a checkbox char. """
    if checked:
        return "\u2611"
    else:
        return "\u2610"

def get_link_status_char(link_status: LinkStatus) -> str:
    """ Returns a checkbox char representing the link status. """
    return get_checkbox_char( link_status == LinkStatus.LINK_UP)

def get_power_char(power: bool) -> str:
    """ Returns a high-voltage symbol if true. """
    if power:
        return "\u26a1"
    else:
        return "  "

def get_display_bytes(bytes: int, short: bool = True) -> str:
    if bytes / (1 if short else 1024) > 1048576 * 1024 * 512:
        return f"{bytes / (1048576.0 * 1048576.0):,.1f}TB"
    if bytes / (1 if short else 1024) > 1048576 * 512:
        return f"{bytes / (1048576.0 * 1024):,.1f}GB"
    return f"{bytes / (1048576.0):,.1f}MB"