"""Exception hierarchy for the DeskCar SDK.

All exceptions raised by this package inherit from :class:`DeskCarError`
so callers can catch a single base type when they want to.
"""

from __future__ import annotations


class DeskCarError(Exception):
    """Base class for all DeskCar SDK errors."""


class TransportError(DeskCarError):
    """Underlying transport (WebSocket / HTTP) failure."""


class ProtocolError(DeskCarError):
    """The car returned a payload we could not decode."""


class NotConnectedError(DeskCarError):
    """An operation that requires an open connection was attempted before
    :meth:`Chassis.connect` (or after :meth:`Chassis.close`)."""


class DeskCarTimeoutError(DeskCarError):
    """An operation exceeded its deadline without completing."""