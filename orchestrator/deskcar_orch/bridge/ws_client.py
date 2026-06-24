"""Thin async wrapper around the ``deskcar`` SDK.

The runtime loop only needs a small surface: drive, stop, set the
speed cap, read the latest state, and react to charge / dock events.
Everything else (discovery, WS framing, error types) is owned by
the ``deskcar`` package; we do not re-export it.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, cast

from deskcar.types import StateSnapshot

from deskcar_orch.geometry import Twist

_LOG = logging.getLogger(__name__)


class WsCar:
    """Async handle to a single DeskCar chassis.

    Holds a :class:`deskcar.Chassis` and maps orchestrator-side types
    onto SDK calls.  The orchestrator owns the lifecycle; this class
    is constructed with an already-open SDK client.
    """

    def __init__(self, car: Any, drain_task: asyncio.Task[None] | None = None) -> None:
        self._car = car
        self._drain_task = drain_task

    @classmethod
    async def connect(cls, host: str, *, speed_cap: int = 180) -> WsCar:
        """Open a connection to ``host`` and apply the PWM cap."""
        from deskcar import Chassis  # local import keeps the bridge optional

        car = Chassis.from_host(host)
        await car.connect()
        drain_task = car.start_event_drain()
        await car.set_speed_cap(speed_cap)
        return cls(car, drain_task)

    async def drive_twist(self, twist: Twist) -> None:
        """Convert a body-frame twist to per-wheel PWM.

        The mapping is the simplest one that works for a differential-
        drive robot: split the linear command across both wheels, add
        the angular component as a wheel differential.
        """
        linear = max(-1.0, min(1.0, twist.linear))
        angular = max(-1.0, min(1.0, twist.angular))
        left = int(255 * (linear + 0.5 * angular))
        right = int(255 * (linear - 0.5 * angular))
        await self._car.drive(left=_clip(left), right=_clip(right))

    async def stop(self) -> None:
        await self._car.stop()

    async def read_state(self) -> StateSnapshot:
        return cast(StateSnapshot, await self._car.read_state())

    async def close(self) -> None:
        if self._drain_task is not None:
            self._drain_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._drain_task
            self._drain_task = None
        await self._car.close()


def _clip(value: int) -> int:
    if value > 255:
        return 255
    if value < -255:
        return -255
    return value
