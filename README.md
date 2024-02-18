# What's this?

A basic Python client for calling the TP-Link Omada controller API.

## Installation

```console
pip install tplink-omada-client
```

## Supported features

Only a subset of the controller's features are supported:
* Automatic Login/Re-login
* Basic controller information
* List sites
* Within site:
    * List Devices (APs, Gateways and Switches)
    * Basic device information
    * Get firmware information and initiating automatic updates
    * Port status and configuraton for Switches
    * Lan port configuration for Access Points
    * Gateway port status and WAN port Connect/Disconnect control

Tested with OC200 on Omada Controller Version 5.5.7 - 5.12.x. Other versions may not be fully compatible.
Version 5.0.x is definitely not compatible.

## CLI

This package provides a simple CLI for interacting with one or more Omada Controllers. To start using the
CLI, you must first target a Controller.

```sh
$ omada -t NAME target --url https://your.omada.controller.here --user admin --password password --site MySite --set-default
```

Where `NAME` is a name of your choosing to identify the targeted controller. `--site` defaults to the Omada
default site name, 'Default'.  If you do not provide a password as an argument, you will be prompted for a
password.

Once you have successfully targeted a controller you can test that things are working by running:

```sh
$ omada devices
```

This will list all the devices being managed by your controller.

To see a list of all the available commands, run:

```sh
$ omada -h
```

You can set up multiple targets (controllers and sites), and specify the target with the `-t <NAME>` parameter.
If you don't specify a target, the default will be used, if that has been set.

The CLI is still young so if there is any functionality you need, please create an issue and let us know.

## Future

The available API surface is quite large. More of this could be exposed in the future.
There is an undocumented Websocket API which could potentially be used to get a stream of updates. However,
I'm not sure how fully featured this subscription channel is on the controller. It seems to be rarely used,
so probably doesn't include client connect/disconnect notifications.

The Omada platform is transitioning to a new OpenAPI API which this library will need to switch over to using
eventually. We will try to avoid breaking changes when this happens, but some will be unavoidable - particularly
authentication.

At the moment, the new API imposes severe daily call limits, even though it is a local device API.
Hopefully this will change, because it is unusable as it stands.

## Contributing

There is a VS Code development container, which sets up all of the requirements for running the package.

## License

MIT Open Source license.
