#!/usr/bin/env python3
""" Cmd line to work out the API. """

import asyncio
import sys
from pprint import pprint
from src.tplink_omada_client.omadaclient import OmadaClient

async def do_the_magic(url: str, site: str, username: str, password: str):
    """ Not a real test client. """

    async with OmadaClient(url, username, password,site=site) as client:
        devices = await client.get_devices()

        print(f"Found {len(devices)} Omada devices.")
        print(f"    {len([d for d in devices if d.type == 'ap'])} Access Points.")
        print(f"    {len([d for d in devices if d.type == 'switch'])} Switches.")
        print(f"    {len([d for d in devices if d.type == 'gateway'])} Routers.")

        pprint(vars(devices[0]))

        # Get full info of all switches
        switches = [await client.get_switch(s) for s in devices if s.type == "switch"]

        pprint(vars(switches[0]))

        #ports = await client.get_switch_ports(switches[0])

        port = await client.get_switch_port(switches[0], switches[0].ports[4])
        print(f"Port index 4: {port.name} Profile: {port.profile_name}")
        pprint(vars(port))

        updated_port = await client.update_switch_port(
            switches[0], port, new_name="Port5")
        pprint(vars(updated_port))

        profiles = await client.get_port_profiles()
        pprint(vars(profiles[0]))

        print("Done.")





def main():
    """ Basic sample test client. """
    if len(sys.argv) < 3:
        print("Usage: client <omada url> <site> [username] [password]")
    else:
        print("Will it work?")

    omadaurl = sys.argv[1]
    site =  sys.argv[2]
    username = "admin" if len(sys.argv) < 4 else sys.argv[3]
    password = "admin" if len(sys.argv) < 5 else sys.argv[4]

    asyncio.run(do_the_magic(omadaurl, site, username, password))


main()
