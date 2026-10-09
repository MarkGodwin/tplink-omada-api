"""Implementation for 'sync-names' command"""

import argparse
import asyncio
import ipaddress
from argparse import _SubParsersAction

import dns.exception
import dns.resolver

from tplink_omada_client import OmadaClientSettings
from tplink_omada_client.clients import OmadaConnectedClient

from .config import get_target_config, to_omada_connection
from .util import get_target_argument


async def command_sync_names(args) -> int:
    """Executes 'sync-names' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    resolver = dns.resolver.Resolver()
    if args["dns_server"]:
        resolver.nameservers = [args["dns_server"]]

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)

        async for connected_client in site_client.get_connected_clients():
            hostname = await _resolve_hostname(connected_client, resolver)
            if hostname is None or hostname == connected_client.name:
                continue

            if not args["dry_run"]:
                await site_client.update_client(connected_client.mac, OmadaClientSettings(name=hostname))

            prefix = "[dry run] " if args["dry_run"] else ""
            print(f"{prefix}{connected_client.mac} {connected_client.ip}: {connected_client.name} -> {hostname}")

    return 0


async def _resolve_hostname(client: OmadaConnectedClient, resolver: dns.resolver.Resolver) -> str | None:
    """Resolve a client's IP address to a short hostname via reverse DNS, if possible.

    Queries via dnspython rather than the OS resolver (socket.gethostbyaddr):
    on macOS, reverse lookups routed through the system resolver (mDNSResponder)
    have been observed to fail even when the same query succeeds via `dig`,
    which - like dnspython - implements its own resolver rather than going
    through mDNSResponder.
    """
    if not client.ip:
        return None
    try:
        answer = await asyncio.to_thread(resolver.resolve_address, client.ip)
    except dns.exception.DNSException:
        return None
    if len(answer) == 0:
        return None
    resolved = str(answer[0].target).rstrip(".")
    short_name = resolved.split(".", maxsplit=1)[0].strip()
    return short_name or None


def _ip_address(value: str) -> str:
    """argparse type callable: validates value is a literal IP address."""
    try:
        ipaddress.ip_address(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"{value!r} is not a valid IP address") from error
    return value


def arg_parser(subparsers: _SubParsersAction) -> None:
    """Configures arguments parser for 'sync-names' command"""
    parser = subparsers.add_parser(
        "sync-names",
        help="Syncs client names to match reverse DNS lookups of their IP addresses",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        help="Show what would be renamed without changing anything",
        action="store_true",
    )
    parser.add_argument(
        "--dns-server",
        dest="dns_server",
        type=_ip_address,
        help="DNS server to query for reverse lookups (defaults to the system's configured resolver)",
        default=None,
    )
    parser.set_defaults(func=command_sync_names)
