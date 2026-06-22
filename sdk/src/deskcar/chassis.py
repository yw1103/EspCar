"""High-level :class:`Chassis` facade for the DeskCar SDK.

This is the surface most users will interact with. A :class:`Chassis`
wraps a :class:`~deskcar.transport.Transport` and exposes a reactive
``drive / stop / set_speed_cap / scan_expansion`` API plus an async
``events()`` stream of state frames.

The class is fully async and is meant to be used as::

    async with await Chassis.discover_first() as car:
        await car.drive(100, 100)
        ...

A :class:`Chassis` may also be used without ``async with`` by calling
:meth:`connect` and :meth:`close` explicitly.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from typing_extensions import Self

from deskcar.discovery import discover, discover_first
from deskcar.transport import Transport
from deskcar.types import (
    ChassisInfo,
    DriveCommand,
    ExpansionDevice,
    ScanExpansionCommand,
    SetSpeedCommand,
    StateSnapshot,
    StopCommand,
)

_LOG = logging.getLogger(__name__)


class Chassis:
    """High-level async client for a single DeskCar chassis."""

    def __init__(self, info: ChassisInfo) -> None:
        self._info = info
        self._transport = Transport(info)

    @classmethod
    async def discover(cls, timeout: float = 2.0) -> list[Self]:
        """Return :class:`Chassis` instances for every car heard on the LAN."""
        return [cls(info) for info in await discover(timeout)]

    @classmethod
    async def discover_first(cls, timeout: float = 2.0) -> Self:
        """Return the first chassis heard, or raise on timeout."""
        return cls(await discover_first(timeout))

    @classmethod
    def from_host(cls, host: str, *, port: int = 80) -> Self:
        """Construct a chassis connected to ``host:port`` without discovery."""
        return cls(ChassisInfo(host=host, port=port))

    @property
    def info(self) -> ChassisInfo:
        return self._info

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def connect(self) -> None:
        await self._transport.open()

    async def close(self) -> None:
        await self._transport.close()

    # ---- reactive control -------------------------------------------------

    async def drive(self, left: int, right: int) -> None:
        """Send a per-wheel PWM command. -255..255 per wheel."""
        cmd = DriveCommand(left=left, right=right)
        await self._transport.send(cmd.model_dump())

    async def stop(self) -> None:
        await self._transport.send(StopCommand().model_dump())

    async def set_speed_cap(self, value: int) -> None:
        """Set the global PWM cap (0..255)."""
        await self._transport.send(SetSpeedCommand(value=value).model_dump())

    # ---- high-level (require vision) -------------------------------------

    # ---- introspection ---------------------------------------------------

    async def scan_expansion(self) -> list[ExpansionDevice]:
        """Force a fresh I2C scan on the magnetic expansion port."""
        await self._transport.send(ScanExpansionCommand().model_dump())
        raw = await self._transport.http_get("/api/v1/devices")
        payload = json.loads(raw)
        return [ExpansionDevice(address=int(d["addr"])) for d in payload.get("devices", [])]

    async def read_state(self) -> StateSnapshot:
        raw = await self._transport.http_get("/api/v1/state")
        return StateSnapshot.model_validate_json(raw)

    def feed(self, payload: dict[str, Any] | bytes) -> None:
        """Test hook: inject a wire frame into the inbound event queue."""
        self._transport.feed(payload)

    # ---- event stream ----------------------------------------------------

    async def events(self) -> AsyncIterator[StateSnapshot | dict[str, Any]]:
        """Yield every state frame and expansion event as a parsed object.

        Unknown frame types are yielded as raw dicts so the consumer can
        still see them.
        """
        async for payload in self._transport.events():
            t = payload.get("type")
            if t == "state":
                yield StateSnapshot.model_validate(payload)
            else:
                yield payload
