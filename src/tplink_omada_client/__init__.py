"""TP-Link Omada API Client"""

from .devices import OmadaSwitchPortDetails
from .omadaclient import OmadaClient, OmadaSite
from .omadasiteclient import (
    AccessPointPortSettings,
    GatewayPortSettings,
    OmadaClientSettings,
    OmadaClientFixedAddress,
    OmadaSiteClient,
    PortProfileOverrides,
    SwitchPortSettings,
)
from .definitions import (
    OmadaControllerUpdateInfo,
    OmadaHardwareUpgradeStatus,
    OmadaHardwareUpdateInfo,
)
from .vpn import OmadaVpnCategory, OmadaVpnPolicy, OmadaVpnType

from . import definitions
from . import exceptions
from . import clients

__all__ = [
    "OmadaClient",
    "OmadaSite",
    "OmadaSiteClient",
    "OmadaControllerUpdateInfo",
    "OmadaHardwareUpgradeStatus",
    "OmadaHardwareUpdateInfo",
    "AccessPointPortSettings",
    "GatewayPortSettings",
    "OmadaClientSettings",
    "OmadaClientFixedAddress",
    "PortProfileOverrides",
    "SwitchPortSettings",
    "OmadaSwitchPortDetails",
    "OmadaVpnCategory",
    "OmadaVpnPolicy",
    "OmadaVpnType",
    "definitions",
    "exceptions",
    "clients",
]
