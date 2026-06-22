"""Tests for the proportional visual-servo controller."""
from __future__ import annotations

import math

import pytest

from deskcar_orch.controller.visual_servo import VisualServo
from deskcar_orch.geometry import Pose


def _servo() -> VisualServo:
    return VisualServo(
        kp_linear=0.8, kp_angular=2.5,
        max_linear_mps=0.30, max_angular_rps=1.6,
        goal_tolerance_m=0.05, goal_tolerance_rad=0.20,
    )


def test_reaches_when_pose_matches_target() -> None:
    cmd = _servo().step(Pose(0.0, 0.0, 0.0), Pose(0.0, 0.0, 0.0))
    assert cmd.reached_goal
    assert cmd.twist.linear == pytest.approx(0.0, abs=1e-9)
    assert cmd.twist.angular == pytest.approx(0.0, abs=1e-9)


def test_drive_forward_when_target_ahead() -> None:
    cmd = _servo().step(Pose(0.0, 0.0, 0.0), Pose(0.5, 0.0, 0.0))
    assert cmd.twist.linear > 0
    assert cmd.twist.angular == pytest.approx(0.0, abs=1e-9)


def test_turn_toward_off_axis_target() -> None:
    # Car heading north (+y) but target is east (+x): must turn left.
    cmd = _servo().step(Pose(0.0, 0.0, theta=math.pi / 2), Pose(1.0, 0.0, 0.0))
    assert cmd.twist.angular < 0  # negative angular = left turn


def test_linear_is_clipped() -> None:
    cmd = _servo().step(Pose(0.0, 0.0, 0.0), Pose(10.0, 0.0, 0.0))
    assert cmd.twist.linear <= 0.30 + 1e-9


def test_angular_is_clipped() -> None:
    cmd = _servo().step(Pose(0.0, 0.0, 0.0), Pose(0.0, 0.0, theta=10.0))
    assert cmd.twist.angular <= 1.6 + 1e-9


def test_close_range_slows_down() -> None:
    far = _servo().step(Pose(0.0, 0.0, 0.0), Pose(0.5, 0.0, 0.0))
    near = _servo().step(Pose(0.0, 0.0, 0.0), Pose(0.10, 0.0, 0.0))
    assert near.twist.linear < far.twist.linear