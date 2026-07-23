"""TP-Link Omada API Client"""

from . import clients, definitions, exceptions
from .definitions import (
    OmadaControllerInfo,
    OmadaControllerUpdateInfo,
    OmadaHardwareUpdateInfo,
    OmadaHardwareUpgradeStatus,
    OmadaSoftwareUpdateInfo,
)
from .devices import OmadaSwitchPortDetails
from .omadaclient import OmadaClient, OmadaSite
from .omadasiteclient import (
    AccessPointPortSettings,
    GatewayPortSettings,
    OmadaClientFixedAddress,
    OmadaClientSettings,
    OmadaSiteClient,
    PortProfileOverrides,
    SwitchPortSettings,
)
from .vpn import OmadaVpnCategory, OmadaVpnPolicy, OmadaVpnType
from .networks import (
    DhcpReservation,
    LanNetwork, LanProfile,
    GatewayAcl, SwitchAcl, EapAcl,
    GroupProfile,
    IpMacBinding,
)

__all__ = [
    "AccessPointPortSettings",
    "DhcpReservation",
    "EapAcl",
    "GatewayAcl",
    "GatewayPortSettings",
    "GroupProfile",
    "IpMacBinding",
    "LanNetwork",
    "LanProfile",
    "OmadaClient",
    "OmadaClientFixedAddress",
    "OmadaClientSettings",
    "OmadaControllerInfo",
    "OmadaControllerUpdateInfo",
    "OmadaHardwareUpdateInfo",
    "OmadaHardwareUpgradeStatus",
    "OmadaSite",
    "OmadaSiteClient",
    "OmadaSoftwareUpdateInfo",
    "OmadaSwitchPortDetails",
    "OmadaVpnCategory",
    "OmadaVpnPolicy",
    "OmadaVpnType",
    "PortProfileOverrides",
    "SwitchAcl",
    "SwitchPortSettings",
    "clients",
    "definitions",
    "exceptions",
]
