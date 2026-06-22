"""Tests for the runtime's pure helpers (the cv2-bound bits are skipped)."""
from __future__ import annotations

import math

import pytest

from deskcar.types import ChargeState, StateSnapshot

from deskcar_orch.config import OrchestratorConfig
from deskcar_orch.geometry import Pose
from deskcar_orch.planning.charge_sm import ChargeState as OrchChargeState
from deskcar_orch.runtime import Orchestrator, _charge_is_active, compute_pad_target


def test_pad_target_along_positive_x() -> None:
    # Tag at the origin, no rotation -> pad sits 4cm in +x, car 8cm in front of pad.
    target = compute_pad_target(
        Pose(0.0, 0.0, 0.0),
        offset=(0.04, 0.0),
        stand_off=0.08,
    )
    assert target.x == pytest.approx(0.04 - 0.08)
    assert target.y == pytest.approx(0.0)
    assert target.theta == pytest.approx(0.0)


def test_pad_target_respects_tag_heading() -> None:
    # Tag at origin but rotated 90 deg CCW -> pad + car move into +y.
    target = compute_pad_target(
        Pose(0.0, 0.0, theta=math.pi / 2),
        offset=(0.04, 0.0),
        stand_off=0.08,
    )
    assert target.x == pytest.approx(0.0, abs=1e-9)
    assert target.y == pytest.approx(0.04 - 0.08)
    assert target.theta == pytest.approx(math.pi / 2)


def test_pad_target_with_lateral_offset() -> None:
    # Tag offset sideways in its own frame: pad sits to the tag's left.
    target = compute_pad_target(
        Pose(0.0, 0.0, 0.0),
        offset=(0.0, 0.04),
        stand_off=0.0,
    )
    assert target.x == pytest.approx(0.0, abs=1e-9)
    assert target.y == pytest.approx(0.04)


def test_charge_is_active_for_detected_charging_full() -> None:
    assert _charge_is_active(StateSnapshot(ts=0, charge=ChargeState.DETECTED))
    assert _charge_is_active(StateSnapshot(ts=0, charge=ChargeState.CHARGING))
    assert _charge_is_active(StateSnapshot(ts=0, charge=ChargeState.FULL))
    assert not _charge_is_active(StateSnapshot(ts=0, charge=ChargeState.IDLE))
    assert not _charge_is_active(StateSnapshot(ts=0, charge=ChargeState.FAULT))


async def test_decide_initial_state_force_dock() -> None:
    orch = Orchestrator(OrchestratorConfig(), force_dock=True)
    await orch._decide_initial_state(None)
    assert orch._sm.state is OrchChargeState.SEEK_DOCK


async def test_decide_initial_state_low_battery_triggers_dock() -> None:
    cfg = OrchestratorConfig()
    orch = Orchestrator(cfg)
    low = StateSnapshot(
        ts=0,
        charge=ChargeState.IDLE,
        soc=cfg.charger.dock_soc_threshold - 5,
    )
    await orch._decide_initial_state(low)
    assert orch._sm.state is OrchChargeState.SEEK_DOCK


async def test_decide_initial_state_already_charging_idles() -> None:
    orch = Orchestrator(OrchestratorConfig())
    await orch._decide_initial_state(
        StateSnapshot(ts=0, charge=ChargeState.CHARGING, soc=50)
    )
    assert orch._sm.state is OrchChargeState.CHARGING


async def test_decide_initial_state_ok_battery_idles() -> None:
    orch = Orchestrator(OrchestratorConfig())
    cfg = OrchestratorConfig()
    ok = StateSnapshot(
        ts=0,
        charge=ChargeState.IDLE,
        soc=cfg.charger.dock_soc_threshold + 10,
    )
    await orch._decide_initial_state(ok)
    assert orch._sm.state is OrchChargeState.IDLE
