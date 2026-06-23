"""Orchestrator runtime: ties vision + controller + state machine to the car.

Only this module orchestrates.  The state machine in
:mod:`deskcar_orch.planning.charge_sm` decides what to *want*; this
loop decides what to *measure* and what to *send to the motors*.

The AprilTag that marks the dock lives on a side board, not on the
charging pad itself, so the camera can see it all the way up to the
moment of contact.  The actual pad position is computed by
:func:`compute_pad_target`, which rotates a known offset from the tag
centre by the tag's heading.
"""
from __future__ import annotations

import asyncio
import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from deskcar.types import ChargeState, StateSnapshot

from deskcar_orch.bridge.ws_client import WsCar
from deskcar_orch.config import OrchestratorConfig
from deskcar_orch.controller.visual_servo import VisualServo
from deskcar_orch.geometry import Pose, Twist
from deskcar_orch.planning.charge_sm import (
    ChargeEvent,
    ChargeMachine,
    ChargeState as OrchChargeState,
)
from deskcar_orch.vision.base import Frame, FrameSource
from deskcar_orch.vision.dock import AprilTagDockDetector, DockObservation
from deskcar_orch.vision.homography import Homography
from deskcar_orch.vision.tracker import ArUcoTracker, MarkerObservation

_LOG = logging.getLogger(__name__)


def _charge_is_active(state: StateSnapshot) -> bool:
    """True when the car reports it is on/near a live dock coil."""
    return state.charge in (
        ChargeState.DETECTED,
        ChargeState.CHARGING,
        ChargeState.FULL,
    )


@dataclass
class _Perception:
    car: MarkerObservation | None = None
    dock: DockObservation | None = None
    last_dock_t: float = 0.0
    last_car_t: float = 0.0


@dataclass
class _StateMonitor:
    """Cache of the last car telemetry read."""

    last_state: StateSnapshot | None = None
    last_state_t: float = 0.0
    charge_active_since: float = 0.0


@dataclass
class _TickResult:
    reached_goal: bool = False


class Orchestrator:
    """One-shot async entry point: ``await Orchestrator(cfg).run()``.

    Set ``force_dock=True`` to start the docking sequence immediately
    regardless of the battery level; this is useful for testing.
    """

    def __init__(
        self,
        cfg: OrchestratorConfig,
        *,
        camera: FrameSource | None = None,
        force_dock: bool = False,
        tracker: "ArUcoTracker | _StubTracker | None" = None,
        dock_det: "AprilTagDockDetector | _StubDockDetector | None" = None,
    ) -> None:
        self._cfg = cfg
        self._force_dock = force_dock
        self._servo = VisualServo(
            kp_linear=cfg.servo.kp_linear,
            kp_angular=cfg.servo.kp_angular,
            max_linear_mps=cfg.servo.max_linear_mps,
            max_angular_rps=cfg.servo.max_angular_rps,
            goal_tolerance_m=cfg.servo.goal_tolerance_m,
            goal_tolerance_rad=cfg.servo.goal_tolerance_rad,
        )
        self._sm = ChargeMachine()
        self._homography = _load_homography_or_identity()
        # Allow tests to inject deterministic stub detectors without
        # pulling OpenCV / drawing synthetic ArUco markers.
        self._tracker = tracker or ArUcoTracker(
            self._homography,
            marker_id=cfg.vision.car_marker_id,
            dictionary=cfg.vision.aruco_dict,
            marker_size_mm=cfg.vision.car_marker_size_mm,
        )
        self._dock_det = dock_det or AprilTagDockDetector(
            self._homography,
            tag_id=cfg.vision.dock_tag_id,
            tag_size_mm=cfg.vision.dock_tag_size_mm,
        )
        self._camera: FrameSource | None = camera
        self._seek_started = 0.0
        self._couple_started = 0.0
        self._undock_started = 0.0
        self._last_tick = _TickResult()
        self._last_sm_state: OrchChargeState | None = None

    async def run(self) -> None:
        car = await WsCar.connect(self._cfg.car_host, speed_cap=180)
        camera = self._camera or _default_camera(self._cfg)
        camera.open()
        try:
            await self._loop(car, camera)
        finally:
            with _suppress(Exception):
                await car.stop()
            await car.close()
            camera.close()

    async def _loop(self, car: WsCar, camera: FrameSource) -> None:
        perception = _Perception()
        monitor = _StateMonitor()
        await self._update_state(car, monitor)
        await self._decide_initial_state(monitor.last_state)

        self._seek_started = time.monotonic()
        self._couple_started = 0.0
        self._undock_started = 0.0

        for frame in camera.frames():
            self._update_perception(perception, frame)
            await self._update_state(car, monitor)
            self._last_tick = _TickResult()
            await self._tick(car, perception, monitor)
            await asyncio.sleep(1.0 / self._cfg.servo.loop_hz)

    async def _decide_initial_state(self, state: StateSnapshot | None) -> None:
        """Start docking if forced, already on the pad, or battery is low."""
        if self._force_dock:
            _LOG.info("force-dock requested")
            self._sm.dispatch(ChargeEvent.BATTERY_LOW)
            return

        if state is not None and _charge_is_active(state):
            _LOG.info("already coupled to dock; monitoring charge")
            self._sm = ChargeMachine(OrchChargeState.CHARGING)
            return

        if state is not None and state.soc is not None:
            if state.soc <= self._cfg.charger.dock_soc_threshold:
                _LOG.info("battery low (%s%%); starting auto-dock", state.soc)
                self._sm.dispatch(ChargeEvent.BATTERY_LOW)
                return

        _LOG.info("battery ok; idling until dock needed")

    def _update_perception(self, p: _Perception, frame: Frame) -> None:
        car_obs = self._tracker.track(frame.image)
        if car_obs is not None:
            p.car = car_obs
            p.last_car_t = frame.timestamp_s
        dock_obs = self._dock_det.detect(frame.image)
        if dock_obs is not None:
            p.dock = dock_obs
            p.last_dock_t = frame.timestamp_s

    async def _update_state(self, car: WsCar, monitor: _StateMonitor) -> None:
        now = time.monotonic()
        if monitor.last_state is not None and now - monitor.last_state_t < 1.0:
            return
        try:
            monitor.last_state = await car.read_state()
            monitor.last_state_t = now
        except Exception as exc:
            _LOG.warning("failed to read car state: %s", exc)

    async def _tick(
        self,
        car: WsCar,
        p: _Perception,
        monitor: _StateMonitor,
    ) -> None:
        state = self._sm.state
        if (
            state is OrchChargeState.SEEK_DOCK
            and self._last_sm_state is not OrchChargeState.SEEK_DOCK
        ):
            self._seek_started = time.monotonic()
        self._last_sm_state = state
        if state is not OrchChargeState.COUPLE:
            self._couple_started = 0.0
        if state is not OrchChargeState.UNDOCK:
            self._undock_started = 0.0
        if state is OrchChargeState.IDLE:
            await car.stop()
            return
        if state is OrchChargeState.SEEK_DOCK:
            await self._seek_tick(car, p)
            return
        if state is OrchChargeState.UNDOCK:
            await self._undock_tick(car, p)
            return
        if p.dock is None or p.car is None:
            if state in (
                OrchChargeState.ALIGN,
                OrchChargeState.APPROACH,
                OrchChargeState.COUPLE,
            ):
                self._sm.dispatch(ChargeEvent.DOCK_LOST)
            await car.stop()
            return
        if state in (OrchChargeState.ALIGN, OrchChargeState.APPROACH):
            await self._servo_tick(car, p.car.pose, p.dock.pose)
            return
        if state is OrchChargeState.COUPLE:
            await self._couple_tick(car, p.car.pose, p.dock.pose, monitor)
            return
        if state is OrchChargeState.CHARGING:
            await self._charging_tick(car, monitor)
            return
        if state is OrchChargeState.FULL:
            await car.stop()
            return
        await car.stop()

    async def _servo_tick(self, car: WsCar, car_pose: Pose, tag_pose: Pose) -> None:
        target = compute_pad_target(
            tag_pose,
            offset=self._cfg.charger.dock_pad_offset_m,
            stand_off=self._cfg.charger.dock_pad_stand_off_m,
        )
        cmd = self._servo.step(car_pose, target)
        self._last_tick.reached_goal = cmd.reached_goal
        await car.drive_twist(cmd.twist)
        if cmd.reached_goal:
            if self._sm.state is OrchChargeState.ALIGN:
                self._sm.dispatch(ChargeEvent.ALIGNED)
            elif self._sm.state is OrchChargeState.APPROACH:
                self._sm.dispatch(ChargeEvent.CLOSE_ENOUGH)

    async def _seek_tick(self, car: WsCar, p: _Perception) -> None:
        if p.dock is not None:
            self._sm.dispatch(ChargeEvent.DOCK_VISIBLE)
            return
        elapsed = time.monotonic() - self._seek_started
        phase = int(elapsed * 2) % 4
        if phase in (0, 1):
            await car.drive_twist(Twist(linear=0.10, angular=0.0))
        else:
            await car.drive_twist(Twist(linear=0.0, angular=0.6))
        if elapsed > self._cfg.charger.seek_max_seconds:
            self._sm.dispatch(ChargeEvent.SEEK_TIMEOUT)

    async def _couple_tick(
        self,
        car: WsCar,
        car_pose: Pose,
        tag_pose: Pose,
        monitor: _StateMonitor,
    ) -> None:
        if self._couple_started == 0.0:
            self._couple_started = time.monotonic()
            monitor.charge_active_since = 0.0

        elapsed = time.monotonic() - self._couple_started
        if elapsed > self._cfg.charger.couple_timeout_s:
            _LOG.warning("couple timeout; retrying alignment")
            self._sm.dispatch(ChargeEvent.COUPLE_TIMEOUT)
            self._couple_started = 0.0
            return

        if monitor.last_state is not None and _charge_is_active(monitor.last_state):
            if monitor.charge_active_since == 0.0:
                monitor.charge_active_since = time.monotonic()
            elif (
                time.monotonic() - monitor.charge_active_since
                >= self._cfg.charger.couple_settle_s
            ):
                _LOG.info("charge coupled after %s s", elapsed)
                self._sm.dispatch(ChargeEvent.COUPLED)
                self._couple_started = 0.0
                await car.stop()
                return
        else:
            monitor.charge_active_since = 0.0

        # Creep forward until the coil couples.
        await car.drive_twist(
            Twist(linear=self._cfg.charger.couple_linear_mps, angular=0.0)
        )

    async def _charging_tick(self, car: WsCar, monitor: _StateMonitor) -> None:
        await car.stop()
        state = monitor.last_state
        if state is None:
            return
        if state.charge is ChargeState.FULL:
            self._sm.dispatch(ChargeEvent.CHARGED)
        elif state.soc is not None and state.soc >= 95:
            _LOG.info("soc reached %s%%; marking full", state.soc)
            self._sm.dispatch(ChargeEvent.CHARGED)

    async def _undock_tick(self, car: WsCar, p: _Perception) -> None:
        if self._undock_started == 0.0:
            self._undock_started = time.monotonic()

        elapsed = time.monotonic() - self._undock_started
        far_enough = False
        if p.car is not None and p.dock is not None:
            dist = math.hypot(
                p.car.pose.x - p.dock.pose.x,
                p.car.pose.y - p.dock.pose.y,
            )
            far_enough = dist > self._cfg.charger.undock_distance_m

        if far_enough or elapsed > self._cfg.charger.undock_timeout_s:
            self._sm.dispatch(ChargeEvent.CLEAR_OF_DOCK)
            self._undock_started = 0.0
            await car.stop()
            return

        await car.drive_twist(
            Twist(linear=-self._cfg.charger.undock_linear_mps, angular=0.0)
        )


def compute_pad_target(
    tag_pose: Pose,
    *,
    offset: tuple[float, float],
    stand_off: float,
) -> Pose:
    """Compute the car pose that lines up with the charging pad.

    The AprilTag centre and the pad centre are separated by ``offset``
    in the tag's body frame (+x forward, +y left).  The car should
    rest at ``stand_off`` metres in front of the pad face, with its
    heading parallel to the pad's.

    All maths is plain 2D: the tag's heading rotates the offset, and
    the stand-off is subtracted along the pad's outward normal.
    """
    ox, oy = offset
    c, s = math.cos(tag_pose.theta), math.sin(tag_pose.theta)
    pad_x = tag_pose.x + ox * c - oy * s
    pad_y = tag_pose.y + ox * s + oy * c
    # Car sits stand_off metres back along the pad's outward normal.
    car_x = pad_x - stand_off * c
    car_y = pad_y - stand_off * s
    return Pose(x=car_x, y=car_y, theta=tag_pose.theta)


def _load_homography_or_identity() -> Homography:
    """Load the calibrated homography if present, else identity.

    Save the calibrated matrix to ``deskcar_orch/calib/homography.npy``
    (see docs/CALIBRATION.md).  Identity is only useful for unit tests.
    """
    calib_path = Path(__file__).with_name("calib") / "homography.npy"
    if calib_path.exists():
        matrix = np.load(calib_path)
        return Homography(matrix=matrix)
    _LOG.warning("no homography calibration found at %s; using identity", calib_path)
    return Homography(matrix=np.eye(3, dtype=np.float64))


def _default_camera(cfg: OrchestratorConfig) -> FrameSource:
    from deskcar_orch.vision.camera import OpenCVCamera

    return OpenCVCamera(
        device=cfg.camera.device,
        width=cfg.camera.width,
        height=cfg.camera.height,
        fps=cfg.camera.fps,
        flip_vertical=cfg.camera.flip_vertical,
    )


class _suppress:
    """Tiny async-friendly ``contextlib.suppress`` stand-in."""

    def __init__(self, *exc: type[BaseException]) -> None:
        self._exc = exc

    def __enter__(self) -> None:
        return None

    def __exit__(self, et: type[BaseException] | None, ev: object, tb: object) -> bool:
        return et is not None and issubclass(et, self._exc)
