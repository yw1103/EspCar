"""DeskCar Python SDK.

Async, typed Python client for the DeskCar ESP32 desktop smart chassis.
Public surface lives in :mod:`deskcar.chassis` and :mod:`deskcar.types`.
"""

from deskcar.chassis import Chassis
from deskcar.exceptions import (
    DeskCarError,
    DeskCarTimeoutError,
    NotConnectedError,
    ProtocolError,
    TransportError,
)
from deskcar.types import (
    ChargeState,
    ChassisInfo,
    ExpansionDevice,
    StateSnapshot,
)

__version__ = "0.1.0"

__all__ = [
    "ChargeState",
    "Chassis",
    "ChassisInfo",
    "DeskCarError",
    "DeskCarTimeoutError",
    "ExpansionDevice",
    "NotConnectedError",
    "ProtocolError",
    "StateSnapshot",
    "TransportError",
]
