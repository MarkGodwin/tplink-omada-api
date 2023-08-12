""" Definitions for Omada enums. """

from abc import ABC
from enum import IntEnum
from typing import Any

class OmadaApiData(ABC):
    def __init__(self, data: dict[str, Any]):
        self._data = data

    def __repr__(self) -> str:
        repr = self.__class__.__name__
        repr += "{"
        for name in self.__dir__():
            if (
                not name.startswith("_")
                and name != "raw_data"
            ):
                repr += f"{name}={getattr(self, name)},"
        repr += "}"
        return repr

    @property
    def raw_data(self) -> dict[str, Any]:
        return self._data

class DeviceStatus(IntEnum):
    """Known status codes for devices."""

    DISCONNECTED = 0
    DISCONNECTED_MIGRATING = 1
    PROVISIONING = 10
    CONFIGURING = 11
    UPGRADING = 12
    REBOOTING = 13
    CONNECTED = 14
    CONNECTED_WIRELESS = 15
    CONNECTED_MIGRATING = 16
    CONNECTED_WIRELESS_MIGRATING = 17
    PENDING = 20
    PENDING_WIRELESS = 21
    ADOPTING = 22
    ADOPTING_WIRELESS = 23
    ADOPT_FAILED = 24
    ADOPT_FAILED_WIRELESS = 25
    MANAGED_EXTERNALLY = 26
    MANAGED_EXTERNALLY_WIRELESS = 27
    HEARTBEAT_MISSED = 30
    HEARTBEAT_MISSED_WIRELESS = 31
    HEARTBEAT_MISSED_MIGRATING = 32
    HEARTBEAT_MISSED_WIRELESS_MIGRATING = 33
    ISOLATED = 40
    ISOLATED_MIGRATING = 41


class DeviceStatusCategory(IntEnum):
    """Known status categories for devices"""

    DISCONNECTED = 0
    CONNECTED = 1
    PENDING = 2
    HEARTBEAT_MISSED = 3
    ISOLATED = 4


class PortType(IntEnum):
    """Known types of switch port."""

    COPPER = 1
    COMBO = 2
    SFP = 3

class GatewayPortType(IntEnum):
    """Known types of gateway port."""
    WAN = 0
    WAN_LAN = 1
    LAN = 2
    SFP_WAN = 3

class GatewayPortMode(IntEnum):
    """Modes of gateway port."""
    DISABLED = -1
    WAN = 0
    LAN = 1

class LinkStatus(IntEnum):
    """Known link statuses."""

    LINK_DOWN = 0
    LINK_UP = 1


class LinkSpeed(IntEnum):
    """Known link speeds."""

    SPEED_AUTO = 0
    SPEED_10_MBPS = 1
    SPEED_100_MBPS = 2
    SPEED_1_GBPS = 3
    SPEED_2_5_GBPS = 4
    SPEED_10_GBPS = 5


class LinkDuplex(IntEnum):
    """Known link duplex modes"""

    AUTO = 0
    HALF = 1
    FULL = 2


class Eth802Dot1X(IntEnum):
    """802.1x auth modes."""

    FORCE_UNAUTHORIZED = 0
    FORCE_AUTHORIZED = 1
    AUTO = 2


class BandwidthControl(IntEnum):
    """Modes of bandwidth control."""

    OFF = 0
    RATE_LIMIT = 1
    STORM_CONTROL = 2


class PoEMode(IntEnum):
    """Settings for PoE policy."""

    NONE = -1
    DISABLED = 0
    ENABLED = 1
    USE_DEVICE_SETTINGS = 2

class AuthenticationStatus:
    """ Client authentication status. """
    CONNECTED = 0
    PENDING = 1
    AUTHORIZED = 2
    AUTH_FREE = 3

class ConnectType(IntEnum):
    """ Client connection types. """
    GUEST_WIRELESS = 0
    WIRELESS = 1
    WIRED = 2

class RadioId(IntEnum):
    """ WiFi radio frequencies """
    FREQ_2_4 = 0
    FREQ_5_1 = 1
    FREQ_5_2 = 2
    FREQ_6   = 3

class WifiMode(IntEnum):
    """ WiFi modes. """
    A   = 0
    B   = 1
    G   = 2
    NA  = 3
    NG  = 4
    AC  = 5
    AXA = 6
    AXG = 7

class LedSetting(IntEnum):
    """ LED Setting """
    OFF           = 0
    ON            = 1
    SITE_SETTINGS = 2
