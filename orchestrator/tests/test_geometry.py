"""Tests for the pure-math geometry primitives."""
from __future__ import annotations

import math

import pytest

from deskcar_orch.geometry import Pose, Twist, Vec2, _wrap_angle


def test_vec2_add_sub() -> None:
    a, b = Vec2(1.0, 2.0), Vec2(0.5, -0.5)
    assert a + b == Vec2(1.5, 1.5)
    assert a - b == Vec2(0.5, 2.5)


def test_vec2_scale() -> None:
    a = Vec2(2.0, -1.0)
    assert a * 0.5 == Vec2(1.0, -0.5)
    assert 3 * a == Vec2(6.0, -3.0)


def test_vec2_norm_and_rotate() -> None:
    v = Vec2(3.0, 4.0)
    assert v.norm() == pytest.approx(5.0)
    # Rotating 90 degrees CCW: (x, y) -> (-y, x)
    rotated = v.rotate(math.pi / 2)
    # Compare component-wise: dataclass __eq__ does not honour
    # pytest.approx, so we cannot rely on a single Vec2() comparison.
    assert rotated.x == pytest.approx(-4.0)
    assert rotated.y == pytest.approx(3.0)


def test_pose_error_to() -> None:
    current = Pose(0.0, 0.0, 0.0)
    target = Pose(1.0, 0.0, math.pi / 4)
    err = current.error_to(target)
    assert err.x == pytest.approx(1.0)
    assert err.y == pytest.approx(0.0)
    assert err.theta == pytest.approx(math.pi / 4)


def test_twist_clipped() -> None:
    t = Twist(linear=2.0, angular=5.0)
    clipped = t.clipped(max_linear=0.5, max_angular=1.0)
    assert clipped.linear == 0.5
    assert clipped.angular == 1.0


def test_wrap_angle_keeps_in_minus_pi_pi() -> None:
    assert _wrap_angle(0.0) == pytest.approx(0.0)
    assert _wrap_angle(math.pi) == pytest.approx(math.pi, abs=1e-9)
    # 3pi should wrap to -pi (or pi - eps)
    wrapped = _wrap_angle(3 * math.pi)
    assert math.fabs(wrapped) <= math.pi + 1e-9
