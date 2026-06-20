"""Implementation for 'port-profiles' command"""

from argparse import ArgumentError, ArgumentParser

from tplink_omada_client.devices import OmadaPortProfile

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_checkbox_char, get_target_argument


def _find_profile(profiles: list[OmadaPortProfile], profile_ref: str) -> OmadaPortProfile:
    matches = [profile for profile in profiles if profile_ref in (profile.profile_id, profile.name)]
    if not matches:
        raise ArgumentError(None, f"Port profile '{profile_ref}' not found")
    if len(matches) > 1:
        matches_display = ", ".join(profile.profile_id for profile in matches)
        raise ArgumentError(None, f"Port profile name '{profile_ref}' is ambiguous: {matches_display}")
    return matches[0]


def _print_profile_row(profile: OmadaPortProfile) -> None:
    profile_type = profile.raw_data.get("type", "")
    print(f"{profile.profile_id:32} {profile_type!s:4} {profile.poe_mode.name:19} {profile.eth_802_1x_control.name:18} {profile.name}")


def _print_profile_details(profile: OmadaPortProfile) -> None:
    print(f"Port Profile: {profile.name}")
    print(f"    ID:                    {profile.profile_id}")
    print(f"    Type:                  {profile.raw_data.get('type', '')}")
    print(f"    PoE:                   {profile.poe_mode.name}")
    print(f"    802.1X:                {profile.eth_802_1x_control.name}")
    print(f"    LLDP-MED:              {get_checkbox_char(profile.lldp_med_enabled)}")
    print(f"    Spanning Tree:         {get_checkbox_char(profile.spanning_tree_enabled)}")
    print(f"    Loopback Detect:       {get_checkbox_char(profile.loopback_detect_enabled)}")
    print(f"    Port Isolation:        {get_checkbox_char(profile.port_isolation_enabled)}")
    if profile.has_eee:
        print(f"    EEE:                   {get_checkbox_char(profile.eee_enabled)}")
    if profile.has_flow_control:
        print(f"    Flow Control:          {get_checkbox_char(profile.flow_control_enabled)}")
    if profile.has_loopback_detect_vlan_based:
        print(f"    VLAN Loopback Detect:  {get_checkbox_char(profile.loopback_detect_vlan_based_enabled)}")


async def command_port_profiles(args) -> int:
    """Executes 'port-profiles' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        profiles = await site_client.get_port_profiles()

        profile_ref = args["profile"]
        if profile_ref:
            profile = _find_profile(profiles, profile_ref)
            _print_profile_details(profile)
            dump_raw_data(args, profile)
        else:
            for profile in profiles:
                _print_profile_row(profile)
                dump_raw_data(args, profile)

    return 0


def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'port-profiles' command"""
    parser: ArgumentParser = subparsers.add_parser("port-profiles", help="Lists switch port profiles")
    parser.set_defaults(func=command_port_profiles)

    parser.add_argument("profile", nargs="?", help="The port profile ID or name")
    parser.add_argument("-d", "--dump", help="Output raw port profile information", action="store_true")
