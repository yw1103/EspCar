"""Tiny geometry primitives for the orchestrator.

No external deps on purpose: every controller / state-machine test should
import this file without dragging OpenCV in.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vec2:
    """A 2D vector in desk (world) coordinates.  Units: meters."""

    x: float
    y: float

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, k: float) -> "Vec2":
        return Vec2(self.x * k, self.y * k)

    __rmul__ = __mul__

    def norm(self) -> float:
        return math.hypot(self.x, self.y)

    def rotate(self, theta: float) -> "Vec2":
        c, s = math.cos(theta), math.sin(theta)
        return Vec2(c * self.x - s * self.y, s * self.x + c * self.y)


@dataclass(frozen=True)
class Pose:
    """2D pose on the desk plane: (x, y) in meters + heading in radians."""

    x: float
    y: float
    theta: float = 0.0

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.theta)

    def error_to(self, target: "Pose") -> "Pose":
        """Return the error pose (target - self) in the world frame."""
        dx = target.x - self.x
        dy = target.y - self.y
        dtheta = _wrap_angle(target.theta - self.theta)
        return Pose(dx, dy, dtheta)


@dataclass(frozen=True)
class Twist:
    """Body-frame velocity command: linear (m/s) + angular (rad/s)."""

    linear: float
    angular: float

    def clipped(self, max_linear: float, max_angular: float) -> "Twist":
        """Return a new Twist with each component magnitude-clamped."""
        return Twist(
            linear=_clamp(self.linear, -abs(max_linear), abs(max_linear)),
            angular=_clamp(self.angular, -abs(max_angular), abs(max_angular)),
        )


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _wrap_angle(angle: float) -> float:
    """Wrap to [-pi, pi] inclusive of +pi.

    The textbook formula maps +pi to -pi (a half-open interval).
    Snap that single edge case back to +pi so callers can rely on a
    symmetric range and can compare against ``math.pi`` directly.
    """
    wrapped = (angle + math.pi) % (2.0 * math.pi) - math.pi
    return math.pi if wrapped == -math.pi else wrapped
