"""Common functionality for multiple commands"""
import argparse
import json

from typing import Any
from re import IGNORECASE, match
from tplink_omada_client.devices import OmadaApiData
from tplink_omada_client.omadasiteclient import OmadaSiteClient

TARGET_ARG: str = "target"

def assert_target_argument(args: dict[str, Any]) -> str:
    """Throws ArgumentError if target arg missing"""
    if args[TARGET_ARG] == "": # The default is now empty
        raise argparse.ArgumentError(None, f"error: Missing --{TARGET_ARG} argument")
    return args[TARGET_ARG]

def get_target_argument(args: dict[str, Any]) -> str:
    return args[TARGET_ARG]

async def get_mac(site_client: OmadaSiteClient, mac_or_name: str) -> str:
    if match('([0-9A-F]{2}[-]){5}[0-9A-F]{2}$',
        string=mac_or_name,
        flags=IGNORECASE):
        return mac_or_name

    device = next((d for d in await site_client.get_devices() if d.name == mac_or_name), None)
    if not device:
        raise argparse.ArgumentError(None, f"Device with name {mac_or_name} not found")
    return device.mac

def dump_raw_data(args: dict[str, Any], data: OmadaApiData):
    if args['dump']:
        print("--- BEGIN RAW DATA ---")
        print(json.dumps(data.raw_data, indent=2))
        print("---  END RAW DATA  ---")
