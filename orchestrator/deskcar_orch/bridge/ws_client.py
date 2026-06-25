"""Thin async wrapper around the ``deskcar`` SDK.

The runtime loop only needs a small surface: drive, stop, set the
speed cap, read the latest state, and react to charge / dock events.
Everything else (discovery, WS framing, error types) is owned by
the ``deskcar`` package; we do not re-export it.
"""
from __future__ import annotations

import asyncio
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

    def __init__(
        self,
        car: Any,
        drain_task: asyncio.Task[None] | None = None,
        *,
        max_linear_mps: float = 0.30,
        max_angular_rps: float = 1.6,
    ) -> None:
        self._car = car
        self._drain_task = drain_task
        self._max_linear_mps = max_linear_mps
        self._max_angular_rps = max_angular_rps

    @classmethod
    async def connect(
        cls,
        host: str,
        *,
        speed_cap: int = 180,
        max_linear_mps: float = 0.30,
        max_angular_rps: float = 1.6,
    ) -> WsCar:
        """Open a connection to ``host`` and apply the PWM cap."""
        from deskcar import Chassis  # local import keeps the bridge optional

        car = Chassis.from_host(host)
        await car.connect()
        await car.set_speed_cap(speed_cap)
        return cls(
            car,
            drain_task,
            max_linear_mps=max_linear_mps,
            max_angular_rps=max_angular_rps,
        )

    async def drive_twist(self, twist: Twist) -> None:
        """Convert a body-frame twist to per-wheel PWM.

        The mapping is the simplest one that works for a differential-
        drive robot: split the linear command across both wheels, add
        the angular component as a wheel differential.
        """
        left, right = twist_to_pwm(
            twist,
            max_linear_mps=self._max_linear_mps,
            max_angular_rps=self._max_angular_rps,
        )
        await self._car.drive(left=left, right=right)

    async def stop(self) -> None:
        await self._car.stop()

    async def read_state(self) -> StateSnapshot:
        return cast(StateSnapshot, await self._car.read_state())

    async def close(self) -> None:
        await self._car.close()


def twist_to_pwm(
    twist: Twist,
    *,
    max_linear_mps: float = 0.30,
    max_angular_rps: float = 1.6,
) -> tuple[int, int]:
    """Map body-frame m/s + rad/s to per-wheel PWM in ``[-255, 255]``.

    ``VisualServo`` and the charge state machine express speeds in SI
    units.  Full-scale linear / angular commands must reach the same
    PWM range as a direct ``Chassis.drive(255, 255)`` call.
    """
    linear = _norm(twist.linear, max_linear_mps)
    angular = _norm(twist.angular, max_angular_rps)
    left = _clip(int(255 * (linear + 0.5 * angular)))
    right = _clip(int(255 * (linear - 0.5 * angular)))
    return left, right


def _norm(value: float, scale: float) -> float:
    if scale <= 0.0:
        return 0.0
    return max(-1.0, min(1.0, value / scale))


def _clip(value: int) -> int:
    if value > 255:
        return 255
    if value < -255:
        return -255
    return value
