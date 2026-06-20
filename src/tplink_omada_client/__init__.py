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
    OmadaControllerInfo,
    OmadaControllerUpdateInfo,
    OmadaHardwareUpgradeStatus,
    OmadaHardwareUpdateInfo,
)

from . import definitions
from . import exceptions
from . import clients

__all__ = [
    "OmadaClient",
    "OmadaSite",
    "OmadaSiteClient",
    "OmadaControllerInfo",
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
    "definitions",
    "exceptions",
    "clients",
]
