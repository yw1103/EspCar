"""Tests for twist -> PWM mapping in the orchestrator bridge."""
from __future__ import annotations

from deskcar_orch.bridge.ws_client import twist_to_pwm
from deskcar_orch.geometry import Twist


def test_seek_forward_reaches_useful_pwm() -> None:
    left, right = twist_to_pwm(Twist(linear=0.10, angular=0.0))
    assert left == right
    assert left >= 80, "0.10 m/s should map to ~1/3 of full PWM, not ~10%"


def test_full_linear_command_hits_pwm_cap() -> None:
    left, right = twist_to_pwm(Twist(linear=0.30, angular=0.0))
    assert left == 255
    assert right == 255


def test_full_angular_command_splits_wheels() -> None:
    left, right = twist_to_pwm(Twist(linear=0.0, angular=1.6))
    assert left == 127
    assert right == -127


def test_couple_creep_is_above_dead_zone() -> None:
    left, right = twist_to_pwm(Twist(linear=0.06, angular=0.0))
    assert left == right
    assert left >= 50
