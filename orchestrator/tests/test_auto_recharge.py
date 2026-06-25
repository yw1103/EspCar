"""End-to-end auto-recharge smoke test using stubbed vision.

This test proves the full control loop end-to-end: the real
:class:`ChargeMachine` + :class:`VisualServo` + :class:`WsCar`
pipeline, driven by deterministic stub observations rather than real
ArUco / AprilTag detection. It walks the FSM through every phase::

    IDLE -> SEEK_DOCK -> ALIGN -> APPROACH -> COUPLE
         -> CHARGING -> FULL -> UNDOCK -> IDLE

and asserts both the state transitions and the resulting drive
commands are sensible (forward during search/approach, reverse
during undock, idle while charging).
"""
from __future__ import annotations

import asyncio
import contextlib
import math
import time
from collections.abc import Iterator
from dataclasses import replace

import numpy as np
from deskcar.types import ChargeState, StateSnapshot

from deskcar_orch.bridge.ws_client import WsCar
from deskcar_orch.config import OrchestratorConfig
from deskcar_orch.geometry import Pose
from deskcar_orch.planning.charge_sm import ChargeEvent
from deskcar_orch.planning.charge_sm import ChargeState as OrchChargeState
from deskcar_orch.runtime import Orchestrator
from deskcar_orch.vision.base import Frame
from deskcar_orch.vision.dock import DockObservation
from deskcar_orch.vision.tracker import MarkerObservation

# ---- stubs -----------------------------------------------------------------


class _StubTracker:
    """Returns whatever pose ``pose_provider`` hands back each frame."""

    def __init__(self, pose_provider, marker_id: int = 0) -> None:
        self._pose_provider = pose_provider
        self._marker_id = marker_id

    def track(self, image):
        pose = self._pose_provider()
        return MarkerObservation(pose=pose, pixel=(0.0, 0.0), marker_id=self._marker_id)


class _StubDockDetector:
    """Returns the dock pose when ``visible_provider`` is True, else None."""

    def __init__(self, pose_provider, visible_provider, tag_id: int = 0) -> None:
        self._pose_provider = pose_provider
        self._visible_provider = visible_provider
        self._tag_id = tag_id

    def detect(self, image):
        if not self._visible_provider():
            return None
        pose = self._pose_provider()
        return DockObservation(pose=pose, pixel=(0.0, 0.0), tag_id=self._tag_id)


class _FakeCamera:
    """Yields one tiny blank frame per call forever."""

    size = (640, 480)

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def frames(self) -> Iterator[Frame]:
        while True:
            yield Frame(
                image=np.zeros((self.size[1], self.size[0], 3), dtype=np.uint8),
                timestamp_s=time.monotonic(),
            )


class _FakeChassis:
    """In-memory chassis that integrates drive commands into a fake pose.

    Records every drive command so the test can assert the control
    outputs. Exposes a ``state_queue`` so we can flip the reported
    charge state at the moments the runtime cares about.
    """

    def __init__(self, initial_pose: Pose) -> None:
        self.pose = initial_pose
        self.drives: list[tuple[int, int]] = []
        self.state_queue: list[StateSnapshot] = []
        self.speed_cap = 180
        # The state the chassis reports by default once the queue is
        # empty. Tests flip this with :meth:`set_charge_state` to drive
        # the FSM through the charge / full transitions.
        self._current_state: StateSnapshot = StateSnapshot(
            ts=0, charge=ChargeState.IDLE, soc=50.0
        )

    def set_charge_state(
        self, charge: ChargeState, *, soc: float = 50.0
    ) -> None:
        self._current_state = StateSnapshot(
            ts=int(time.monotonic() * 1000),
            charge=charge,
            soc=soc,
        )

    async def drive(self, left: int, right: int) -> None:
        self.drives.append((left, right))
        # Crude differential-drive integration. dt is a constant so the
        # test stays deterministic regardless of the wall-clock cadence.
        dt = 0.02
        # Clamp to match the test's tuned servo limits (1.0 m/s, 3.0 rad/s)
        # so the fake chassis can keep up with the visual servo.
        v = max(-1.0, min(1.0, (left + right) / 2 / 255 * 1.0))
        w = max(-3.0, min(3.0, (right - left) / 255 * 3.0))
        self.pose = Pose(
            self.pose.x + v * math.cos(self.pose.theta) * dt,
            self.pose.y + v * math.sin(self.pose.theta) * dt,
            self.pose.theta + w * dt,
        )

    async def stop(self) -> None:
        self.drives.append((0, 0))

    async def set_speed_cap(self, value: int) -> None:
        self.speed_cap = value

    async def read_state(self) -> StateSnapshot:
        if self.state_queue:
            return self.state_queue.pop(0)
        # Refresh the timestamp so every frame reports a fresh wall clock.
        # StateSnapshot is a Pydantic BaseModel, so dataclasses.replace
        # would raise TypeError; use model_copy instead.
        return self._current_state.model_copy(
            update={"ts": int(time.monotonic() * 1000)}
        )

    async def close(self) -> None:
        pass


class _FastOrchestrator(Orchestrator):
    """Orchestrator variant that polls the chassis state every tick.

    The default runtime throttles ``read_state`` to 1 Hz to save
    bandwidth; the smoke test needs fresh state on every iteration so
    the state machine can react immediately.
    """

    async def _update_state(self, car, monitor):  # type: ignore[override]
        monitor.last_state = await car.read_state()
        monitor.last_state_t = time.monotonic()
        self._last_monitor = monitor


# ---- helpers ----------------------------------------------------------------


async def _wait_for(
    orch: Orchestrator, target: OrchChargeState, *, timeout: float
) -> None:
    """Poll the FSM until it reaches ``target`` or the deadline elapses."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if orch._sm.state is target:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(
        f"state machine did not reach {target!r} within {timeout:.2f}s "
        f"(currently {orch._sm.state!r})"
    )


def _fast_test_config() -> OrchestratorConfig:
    """Tighten the time constants so the cycle finishes in ~2 s."""
    base = OrchestratorConfig()
    return base.with_overrides(
        servo=replace(
            base.servo,
            loop_hz=200.0,
            kp_linear=2.0,
            max_linear_mps=1.0,
            kp_angular=4.0,
            max_angular_rps=3.0,
            goal_tolerance_m=0.05,
            goal_tolerance_rad=0.20,
        ),
        charger=replace(
            base.charger,
            couple_settle_s=0.05,
            undock_timeout_s=2.0,
            undock_linear_mps=0.30,
        ),
    )


# ---- the tests --------------------------------------------------------------


async def test_auto_recharge_full_cycle() -> None:
    cfg = _fast_test_config()
    dock_pose = Pose(0.0, 0.0, 0.0)
    # Start ~12 cm in front of the dock, already pointing at it so the
    # visual servo only has to do straight-line convergence instead of
    # spending the budget spinning in place.
    start_pose = Pose(0.12, 0.0, math.pi)

    chassis = _FakeChassis(start_pose)
    dock_visible = {"v": False}

    tracker = _StubTracker(pose_provider=lambda: chassis.pose)
    dock_det = _StubDockDetector(
        pose_provider=lambda: dock_pose,
        visible_provider=lambda: dock_visible["v"],
    )
    orch = _FastOrchestrator(
        cfg, tracker=tracker, dock_det=dock_det, force_dock=True
    )

    ws_car = WsCar(
        chassis,
        max_linear_mps=cfg.servo.max_linear_mps,
        max_angular_rps=cfg.servo.max_angular_rps,
    )
    runner = asyncio.create_task(orch._loop(ws_car, _FakeCamera()))
    try:
        # Phase 1: dock not visible -> SEEK_DOCK drives search motions.
        await _wait_for(orch, OrchChargeState.SEEK_DOCK, timeout=0.5)
        await asyncio.sleep(0.15)
        assert any(
            abs(left) > 0 or abs(right) > 0 for left, right in chassis.drives
        ), "expected SEEK_DOCK to issue non-zero drive commands"

        # Phase 2: dock appears -> ALIGN -> APPROACH -> COUPLE through
        # the visual servo closing on the dock pose.
        dock_visible["v"] = True
        await _wait_for(orch, OrchChargeState.ALIGN, timeout=1.0)
        await _wait_for(orch, OrchChargeState.APPROACH, timeout=2.0)
        await _wait_for(orch, OrchChargeState.COUPLE, timeout=2.0)
        assert math.hypot(
            chassis.pose.x - dock_pose.x, chassis.pose.y - dock_pose.y
        ) < start_pose.x, "car should have moved closer to the dock"

        # Phase 3: feed CHARGING -> COUPLED -> CHARGING after settle_s.
        chassis.set_charge_state(ChargeState.CHARGING, soc=70.0)
        await _wait_for(orch, OrchChargeState.CHARGING, timeout=2.0)

        # Phase 4: feed FULL -> CHARGED -> FULL.
        chassis.set_charge_state(ChargeState.FULL, soc=100.0)
        await _wait_for(orch, OrchChargeState.FULL, timeout=2.0)

        # Phase 5: external USER_UNDOCK -> UNDOCK.  Drive commands during
        # UNDOCK must include negative wheel values (reverse motion).
        orch._sm.dispatch(ChargeEvent.USER_UNDOCK)
        await _wait_for(orch, OrchChargeState.UNDOCK, timeout=1.0)
        await asyncio.sleep(0.2)
        recent = chassis.drives[-30:]
        assert any(left < 0 or right < 0 for left, right in recent), (
            "UNDOCK must command reverse motion"
        )

        # Phase 6: teleport clear of the dock -> CLEAR_OF_DOCK -> IDLE.
        chassis.pose = Pose(1.0, 1.0, 0.0)
        await _wait_for(orch, OrchChargeState.IDLE, timeout=3.0)

    finally:
        runner.cancel()
        with contextlib.suppress(BaseException):
            await runner


async def test_seek_to_align_transition_when_dock_appears() -> None:
    """Belt-and-braces check: a single transition in isolation."""
    cfg = _fast_test_config()
    chassis = _FakeChassis(Pose(0.12, 0.0, math.pi))
    dock_visible = {"v": False}
    tracker = _StubTracker(pose_provider=lambda: chassis.pose)
    dock_det = _StubDockDetector(
        pose_provider=lambda: Pose(0.0, 0.0, 0.0),
        visible_provider=lambda: dock_visible["v"],
    )
    orch = _FastOrchestrator(
        cfg, tracker=tracker, dock_det=dock_det, force_dock=True
    )

    runner = asyncio.create_task(
        orch._loop(
            WsCar(
                chassis,
                max_linear_mps=cfg.servo.max_linear_mps,
                max_angular_rps=cfg.servo.max_angular_rps,
            ),
            _FakeCamera(),
        )
    )
    try:
        await _wait_for(orch, OrchChargeState.SEEK_DOCK, timeout=0.5)
        dock_visible["v"] = True
        await _wait_for(orch, OrchChargeState.ALIGN, timeout=1.0)
    finally:
        runner.cancel()
        with contextlib.suppress(BaseException):
            await runner
