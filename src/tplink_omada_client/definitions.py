"""Definitions for Omada enums."""

from abc import ABC
from enum import IntEnum
from typing import Any


class OmadaApiData(ABC):
    """Base representation of Omada API data."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    def __repr__(self) -> str:
        repr_str = self.__class__.__name__
        repr_str += "{"
        for name in self.__dir__():
            if not name.startswith("_") and name != "raw_data":
                repr_str += f"{name}={getattr(self, name)},"
        repr_str += "}"
        return repr_str

    @property
    def raw_data(self) -> dict[str, Any]:
        """Raw data obtained from Omada API."""
        return self._data


class DeviceStatus(IntEnum):
    """Known status codes for devices."""

    UNKNOWN = -1
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

    @classmethod
    def _missing_(cls, _):
        return DeviceStatus.UNKNOWN


class DeviceStatusCategory(IntEnum):
    """Known status categories for devices"""

    UNKNOWN = -1
    DISCONNECTED = 0
    CONNECTED = 1
    PENDING = 2
    HEARTBEAT_MISSED = 3
    ISOLATED = 4

    @classmethod
    def _missing_(cls, _):
        return DeviceStatusCategory.UNKNOWN


class PortType(IntEnum):
    """Known types of switch port."""

    UNKNOWN = -1
    COPPER = 1
    COMBO = 2
    SFP = 3

    @classmethod
    def _missing_(cls, _):
        return PortType.UNKNOWN


class GatewayPortType(IntEnum):
    """Known types of gateway port."""

    UNKNOWN = -1
    WAN = 0
    WAN_LAN = 1
    LAN = 2
    SFP_WAN = 3

    @classmethod
    def _missing_(cls, _):
        return GatewayPortType.UNKNOWN


class GatewayPortMode(IntEnum):
    """Modes of gateway port."""

    DISABLED = -1
    WAN = 0
    LAN = 1

    @classmethod
    def _missing_(cls, _):
        return GatewayPortMode.DISABLED


class LinkStatus(IntEnum):
    """Known link statuses."""

    UNKNOWN = -1
    LINK_DOWN = 0
    LINK_UP = 1

    @classmethod
    def _missing_(cls, _):
        return LinkStatus.UNKNOWN


class LinkSpeed(IntEnum):
    """Known link speeds."""

    UNKNOWN = -1
    SPEED_AUTO = 0
    SPEED_10_MBPS = 1
    SPEED_100_MBPS = 2
    SPEED_1_GBPS = 3
    SPEED_2_5_GBPS = 4
    SPEED_10_GBPS = 5

    @classmethod
    def _missing_(cls, _):
        return LinkSpeed.UNKNOWN


class LinkDuplex(IntEnum):
    """Known link duplex modes"""

    UNKNOWN = -1
    AUTO = 0
    HALF = 1
    FULL = 2

    @classmethod
    def _missing_(cls, _):
        return LinkDuplex.UNKNOWN


class Eth802Dot1X(IntEnum):
    """802.1x auth modes."""

    UNKNOWN = -1
    FORCE_UNAUTHORIZED = 0
    FORCE_AUTHORIZED = 1
    AUTO = 2

    @classmethod
    def _missing_(cls, _):
        return Eth802Dot1X.UNKNOWN


class BandwidthControl(IntEnum):
    """Modes of bandwidth control."""

    UNKNOWN = -1
    OFF = 0
    RATE_LIMIT = 1
    STORM_CONTROL = 2

    @classmethod
    def _missing_(cls, _):
        return BandwidthControl.UNKNOWN


class PoEMode(IntEnum):
    """Settings for PoE policy."""

    NONE = -1
    DISABLED = 0
    ENABLED = 1
    USE_DEVICE_SETTINGS = 2

    @classmethod
    def _missing_(cls, _):
        return PoEMode.NONE


class AuthenticationStatus:
    """Client authentication status."""

    UNKNOWN = -1
    CONNECTED = 0
    PENDING = 1
    AUTHORIZED = 2
    AUTH_FREE = 3

    @classmethod
    def _missing_(cls, _):
        return AuthenticationStatus.UNKNOWN


class ConnectType(IntEnum):
    """Client connection types."""

    UNKNOWN = -1
    GUEST_WIRELESS = 0
    WIRELESS = 1
    WIRED = 2

    @classmethod
    def _missing_(cls, _):
        return ConnectType.UNKNOWN


class RadioId(IntEnum):
    """WiFi radio frequencies"""

    UNKNOWN = -1
    FREQ_2_4 = 0
    FREQ_5_1 = 1
    FREQ_5_2 = 2
    FREQ_6 = 3

    @classmethod
    def _missing_(cls, _):
        return RadioId.UNKNOWN


class WifiMode(IntEnum):
    """WiFi modes."""

    UNKNOWN = -1
    A = 0
    B = 1
    G = 2
    NA = 3
    NG = 4
    AC = 5
    AXA = 6
    AXG = 7

    @classmethod
    def _missing_(cls, _):
        return WifiMode.UNKNOWN


class LedSetting(IntEnum):
    """LED Setting"""

    UNKNOWN = -1
    OFF = 0
    ON = 1
    SITE_SETTINGS = 2

    @classmethod
    def _missing_(cls, _):
        return LedSetting.UNKNOWN
