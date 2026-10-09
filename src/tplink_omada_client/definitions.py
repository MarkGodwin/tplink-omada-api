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


class OmadaControllerInfo(OmadaApiData):
    """Information returned by the Omada Controller /api/info endpoint."""

    @property
    def controller_version(self) -> str:
        """Controller software version."""
        return self._data["controllerVer"]

    @property
    def api_version(self) -> str | None:
        """Controller API version."""
        return self._data.get("apiVer")

    @property
    def configured(self) -> bool | None:
        """Whether the controller setup wizard has been completed."""
        return self._data.get("configured")

    @property
    def type(self) -> int | None:
        """Controller type as returned by the Omada API."""
        return self._data.get("type")

    @property
    def support_app(self) -> bool | None:
        """Whether the controller supports the Omada app."""
        return self._data.get("supportApp")

    @property
    def omadac_id(self) -> str:
        """Controller ID."""
        return self._data["omadacId"]

    @property
    def registered_root(self) -> bool | None:
        """Whether the root account is registered."""
        return self._data.get("registeredRoot")

    @property
    def omadac_category(self) -> str | None:
        """Controller category."""
        return self._data.get("omadacCategory")

    @property
    def msp_mode(self) -> bool | None:
        """Whether the controller is running in MSP mode."""
        return self._data.get("mspMode")

    @property
    def omada_cloud_url(self) -> str | None:
        """Omada cloud URL."""
        return self._data.get("omadaCloudUrl")


class OmadaControllerType(OmadaApiData):
    """Information returned by the Omada controller type endpoint."""

    @property
    def is_soft_controller(self) -> bool:
        """Whether this is an Omada Software Controller."""
        return self._data["isSoftController"]

    @property
    def combined_gateway(self) -> bool:
        """Whether this controller is running on a combined gateway."""
        return self._data.get("combinedGateway", False)


class OmadaControllerStatus(OmadaApiData):
    """Status information returned by the Omada controller."""

    @property
    def name(self) -> str | None:
        """Controller display name."""
        name = self._data.get("name")
        if not isinstance(name, str):
            return None

        name = name.strip()
        return name or None

    @property
    def mac(self) -> str:
        """Controller MAC address."""
        return self._data["macAddress"]

    @property
    def uptime(self) -> int:
        """Controller uptime in seconds."""
        return self._data["upTime"]

    @property
    def controller_version(self) -> str:
        """Controller version reported by the status endpoint."""
        return self._data["controllerVersion"]

    @property
    def current_version(self) -> str:
        """Currently installed controller version."""
        return self.controller_version

    @property
    def model(self) -> str:
        """Controller hardware model, or a generic fallback."""
        model = self._data.get("model")
        if isinstance(model, str) and (model := model.strip()):
            return model

        return "Controller"


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


class NetworkTagsSetting(IntEnum):
    """Network tags settings for ports."""

    UNKNOWN = -1
    ALLOW_ALL = 0
    BLOCK_ALL = 1
    CUSTOM = 2

    @classmethod
    def _missing_(cls, _):
        return NetworkTagsSetting.UNKNOWN


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

    @property
    def settings_key(self) -> str:
        """Name of the field the controller uses for this radio's settings."""
        return _RADIO_SETTINGS_KEYS[self]

    @property
    def status_key(self) -> str:
        """Name of the field the controller uses for this radio's live status."""
        return _RADIO_STATUS_KEYS[self]


_RADIO_SETTINGS_KEYS = {
    RadioId.FREQ_2_4: "radioSetting2g",
    RadioId.FREQ_5_1: "radioSetting5g",
    RadioId.FREQ_5_2: "radioSetting5g2",
    RadioId.FREQ_6: "radioSetting6g",
}

_RADIO_STATUS_KEYS = {
    RadioId.FREQ_2_4: "wp2g",
    RadioId.FREQ_5_1: "wp5g",
    RadioId.FREQ_5_2: "wp5g2",
    RadioId.FREQ_6: "wp6g",
}


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


class ChannelWidth(IntEnum):
    """Channel width of an access point radio.

    The values form a single ladder shared by all bands. The AUTO_* members let
    the access point pick any width up to the widest one named, and the
    controller offers only one of them per band: AUTO_40_20 on 2.4GHz,
    AUTO_80_40_20 on 5GHz, and AUTO_160_80_40_20 on 6GHz.

    Which fixed widths a radio accepts depends on the hardware and on the
    regulatory region, so the controller is the authority on what is legal.
    """

    UNKNOWN = -1
    WIDTH_20 = 2
    WIDTH_40 = 3
    AUTO_40_20 = 4
    WIDTH_80 = 5
    AUTO_80_40_20 = 6
    WIDTH_160 = 7
    AUTO_160_80_40_20 = 8
    WIDTH_240 = 9
    WIDTH_320 = 10

    @classmethod
    def _missing_(cls, _):
        return ChannelWidth.UNKNOWN


class OmadaHardwareUpdateInfo(OmadaApiData):
    """Information about available hardware firmware updates."""

    @property
    def upgrade(self) -> bool:
        """Whether a firmware upgrade is available."""
        return self._data["upgrade"]

    @property
    def latest_version(self) -> str | None:
        """The latest available firmware version."""
        return self._data.get("latestVersion", self.current_version)

    @property
    def current_version(self) -> str | None:
        """The currently installed firmware version, if the controller reports it."""
        return self._data.get("currentVersion")

    @property
    def release_notes(self) -> str | None:
        """Release notes for the latest firmware version."""
        notes = self._data.get("fwReleaseLog")
        if notes is None:
            notes = self._data.get("releaseLog")
        return notes

    @property
    def download_link(self) -> str | None:
        """Download link for the available controller update."""
        download_link = self._data.get("downloadLink")
        if not isinstance(download_link, str):
            return None

        download_link = download_link.strip()
        return download_link or None

    @property
    def release_url(self) -> str | None:
        """URL with information or a download for the latest release."""
        return self.download_link


class OmadaSoftwareUpdateInfo(OmadaApiData):
    """Information about available software controller updates."""

    @property
    def upgrade(self) -> bool:
        """Whether a software upgrade is available."""
        return self._data["upgrade"]

    @property
    def latest_version(self) -> str | None:
        """The latest available software version."""
        return self._data.get("latestVersion", self.current_version)

    @property
    def current_version(self) -> str | None:
        """The currently installed software version, if the controller reports it."""
        return self._data.get("currentVersion")

    @property
    def release_notes(self) -> str | None:
        """Release notes for the latest software version."""
        notes = self._data.get("releaseLog")
        if notes is None:
            notes = self._data.get("fwReleaseLog")
        return notes

    @property
    def download_link(self) -> str | None:
        """Download link for the available controller update."""
        download_link = self._data.get("downloadLink")
        if not isinstance(download_link, str):
            return None

        download_link = download_link.strip()
        return download_link or None

    @property
    def release_url(self) -> str | None:
        """URL with information or a download for the latest release."""
        return self.download_link


class OmadaControllerUpdateInfo(OmadaApiData):
    """Normalized information about available controller updates."""

    @property
    def hardware(self) -> OmadaHardwareUpdateInfo | None:
        """Information about available hardware controller firmware updates."""
        if self._data.get("hardware") is None:
            return None

        return OmadaHardwareUpdateInfo(self._data["hardware"])

    @property
    def software(self) -> OmadaSoftwareUpdateInfo | None:
        """Information about available software controller updates."""
        if self._data.get("software") is None:
            return None

        return OmadaSoftwareUpdateInfo(self._data["software"])

    @property
    def update(self) -> OmadaHardwareUpdateInfo | OmadaSoftwareUpdateInfo | None:
        """Update information for the current controller type."""
        return self.hardware or self.software

    @property
    def upgrade(self) -> bool:
        """Whether a controller update is available."""
        return self.update.upgrade if self.update is not None else False

    @property
    def current_version(self) -> str | None:
        """Currently installed controller version."""
        return self.update.current_version if self.update is not None else None

    @property
    def latest_version(self) -> str | None:
        """Latest available controller version."""
        return self.update.latest_version if self.update is not None else None

    @property
    def release_notes(self) -> str | None:
        """Release notes for the latest controller version."""
        return self.update.release_notes if self.update is not None else None

    @property
    def release_url(self) -> str | None:
        """URL with information or a download for the latest release."""
        return self.update.release_url if self.update is not None else None


class OmadaHardwareUpgradeStatus(OmadaApiData):
    """Information about the status of a hardware controller firmware upgrade."""

    @property
    def upgrade_status(self) -> int:
        """The current status of the firmware upgrade process."""
        return self._data["upgradeStatus"]

    @property
    def upgrade_msg(self) -> str:
        """Any message associated with the current firmware upgrade status."""
        return self._data.get("upgradeMsg", "")

    @property
    def upgrade_time(self) -> int:
        """How often to refresh to watch the download progress?"""
        return self._data.get("upgradeTime", 0)

    @property
    def download_progress(self) -> int:
        """The current progress of the firmware download, as a percentage."""
        return self._data.get("downloadProgress", 0)

    @property
    def reboot_time(self) -> int:
        """How long after the download completes before we expect the controller to come back online, in seconds."""
        return self._data.get("rebootTime", 300)
