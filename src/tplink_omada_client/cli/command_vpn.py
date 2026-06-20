"""Implementation for 'vpn' command"""

from argparse import ArgumentError, ArgumentParser

from tplink_omada_client.vpn import OmadaVpnPolicy

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_checkbox_char, get_target_argument


def _find_policy(policies: list[OmadaVpnPolicy], policy_ref: str) -> OmadaVpnPolicy:
    matches = [
        policy
        for policy in policies
        if policy_ref in (policy.policy_id, policy.unique_id, policy.name)
    ]
    if not matches:
        raise ArgumentError(None, f"VPN policy '{policy_ref}' not found")
    if len(matches) > 1:
        matches_display = ", ".join(policy.unique_id for policy in matches)
        raise ArgumentError(None, f"VPN policy name '{policy_ref}' is ambiguous: {matches_display}")
    return matches[0]


def _print_policy(policy: OmadaVpnPolicy) -> None:
    print(f"{policy.policy_id:32} {policy.category.value:12} {get_checkbox_char(policy.enabled)} {policy.vpn_type_name:10} {policy.name}")


async def command_vpn(args) -> int:
    """Executes 'vpn' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        policies = await site_client.get_vpn_policies()

        policy_ref = args["policy"]
        if policy_ref:
            policy = _find_policy(policies, policy_ref)
            if args["enable"] or args["disable"]:
                enabled = bool(args["enable"])
                await site_client.set_vpn_policy_enabled(policy.policy_id, enabled)
                print(f"VPN policy '{policy.name}' is now {'enabled' if enabled else 'disabled'}")
                policies = await site_client.get_vpn_policies()
                policy = _find_policy(policies, policy.policy_id)

            _print_policy(policy)
            dump_raw_data(args, policy)
        else:
            for policy in policies:
                _print_policy(policy)
                dump_raw_data(args, policy)

    return 0


def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'vpn' command"""
    parser: ArgumentParser = subparsers.add_parser("vpn", help="Lists and controls VPN policies")
    parser.set_defaults(func=command_vpn)

    parser.add_argument("policy", nargs="?", help="The VPN policy ID, unique ID or name")
    enabled_group = parser.add_mutually_exclusive_group()
    enabled_group.add_argument("--enable", help="Enable the VPN policy", action="store_true")
    enabled_group.add_argument("--disable", help="Disable the VPN policy", action="store_true")
    parser.add_argument("-d", "--dump", help="Output raw VPN policy information", action="store_true")
