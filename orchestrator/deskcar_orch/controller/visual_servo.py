"""Proportional visual servo: world-frame pose error -> body twist.

Inputs come from the vision stack (ArUco + AprilTag + homography);
outputs are :class:`ServoCommand` consumed by :mod:`bridge.ws_client`.

The controller is intentionally pure-Python: no asyncio, no OpenCV.
That makes it trivial to unit-test the closed-loop math on a headless box.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from deskcar_orch.geometry import Pose, Twist, _wrap_angle


@dataclass(frozen=True)
class ServoCommand:
    """One cycle of the visual-servo output."""

    twist: Twist
    reached_goal: bool


class VisualServo:
    """P-controller from world-frame pose error to body-frame twist.

    Linear velocity is along the world-frame error vector, projected
    into the body frame.  Angular velocity is a proportional heading
    hold.  Tuning lives in :class:`ServoConfig`; see ``configs/default.yaml``.
    """

    def __init__(
        self,
        *,
        kp_linear: float = 0.8,
        kp_angular: float = 2.5,
        max_linear_mps: float = 0.30,
        max_angular_rps: float = 1.6,
        goal_tolerance_m: float = 0.05,
        goal_tolerance_rad: float = 0.20,
    ) -> None:
        self.kp_linear = kp_linear
        self.kp_angular = kp_angular
        self.max_linear = max_linear_mps
        self.max_angular = max_angular_rps
        self.tol_m = goal_tolerance_m
        self.tol_rad = goal_tolerance_rad

    def step(self, current: Pose, target: Pose) -> ServoCommand:
        """One closed-loop step.

        ``current`` is the latest car pose from ArUco; ``target`` is
        the dock pose (or a sub-goal on the way to the dock).
        """
        dx = target.x - current.x
        dy = target.y - current.y
        dist = math.hypot(dx, dy)
        heading_to_target = math.atan2(dy, dx)
        heading_error = _wrap_angle(heading_to_target - current.theta)

        # Body-frame linear: project the world error onto the car's
        # forward axis.  Angular holds the heading.
        v_world = self.kp_linear * dist
        v_body = v_world * math.cos(heading_error)
        w = self.kp_angular * heading_error

        # Slow down as we get close so we do not slam into the dock.
        if dist < 0.20:
            v_body *= dist / 0.20

        twist = Twist(linear=v_body, angular=w).clipped(
            max_linear=self.max_linear,
            max_angular=self.max_angular,
        )

        reached = dist < self.tol_m and abs(heading_error) < self.tol_rad
        return ServoCommand(twist=twist, reached_goal=reached)