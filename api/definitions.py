""" Definitions for Omada enums. """

from enum import IntEnum

class DeviceStatus(IntEnum):
    """ Known status codes for devices. """
    DISCONNECTED = 0
    DISCONNECTED_MIGRATING = 1
    PROVISIONING  = 10
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
    """ Known status categories for devices """
    DISCONNECTED = 0
    CONNECTED = 1
    PENDING = 2
    HEARTBEAT_MISSED = 3
    ISOLATED = 4

class PortType(IntEnum):
    """ Known types of switch port. """
    COPPER = 1
    COMBO = 2
    SFP = 3

class LinkStatus(IntEnum):
    """ Known link statuses. """
    LINK_UP = 0
    LINK_DOWN = 2

class LinkSpeed(IntEnum):
    """ Known link speeds. """
    SPEED_AUTO = 0
    SPEED_10_MBPS = 1
    SPEED_100_MBDS = 2
    SPEED_1_GBPS = 3
    SPEED_10_GBPS = 4

class LinkDuplex(IntEnum):
    """ Known link duplex modes """
    AUTO = 0
    HALF = 1
    FULL = 2

class Eth802Dot1X(IntEnum):
    """ 802.1x auth modes. """
    FORCE_UNAUTHORIZED = 0
    FORCE_AUTHORIZED = 1
    AUTO = 2

class BandwidthControl(IntEnum):
    """ Modes of bandwidth control. """
    OFF = 0
    RATE_LIMIT = 1
    STORM_CONTROL = 2

class PoEMode(IntEnum):
    """ Settings for PoE policy. """
    DISABLED = 0
    ENABLED = 1
    USE_DEVICE_SETTINGS = 2
