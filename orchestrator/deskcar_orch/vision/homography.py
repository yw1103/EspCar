"""Pixel <-> world (desk plane) homography.

A single 3x3 matrix maps (u, v) image coordinates to (X, Y) in meters
measured from the desk origin.  The matrix is meant to be calibrated once
at install time and reused forever; see ``docs/CALIBRATION.md``.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from deskcar_orch.geometry import Pose, Vec2


@dataclass(frozen=True)
class Homography:
    """Pixel -> world mapping, expressed as a 3x3 matrix."""

    matrix: np.ndarray  # shape (3, 3), dtype float64

    def __post_init__(self) -> None:
        if self.matrix.shape != (3, 3):
            raise ValueError(f"homography must be 3x3, got {self.matrix.shape}")

    @classmethod
    def from_corners(
        cls,
        pixel_pts: list[tuple[float, float]],
        world_pts: list[tuple[float, float]],
    ) -> Homography:
        """Build a homography from 4+ (pixel, world) point pairs."""
        if len(pixel_pts) != len(world_pts) or len(pixel_pts) < 4:
            raise ValueError("need at least 4 matching point pairs")
        src = np.asarray(pixel_pts, dtype=np.float64)
        dst = np.asarray(world_pts, dtype=np.float64)
        H, _ = cv2_find_homography(src, dst)
        if H is None:
            raise ValueError("cv2.findHomography returned None; points may be collinear")
        return cls(matrix=H)

    def pixel_to_world(self, u: float, v: float) -> Vec2:
        out = self.matrix @ np.array([u, v, 1.0], dtype=np.float64)
        if abs(out[2]) < 1e-9:
            raise ValueError("degenerate homography: w ~= 0")
        return Vec2(float(out[0] / out[2]), float(out[1] / out[2]))

    def pose_from_pixel(self, u: float, v: float, theta_rad: float) -> Pose:
        p = self.pixel_to_world(u, v)
        return Pose(p.x, p.y, theta_rad)

    def world_to_pixel(self, world: Vec2) -> tuple[float, float]:
        M_inv = np.linalg.inv(self.matrix)
        out = M_inv @ np.array([world.x, world.y, 1.0], dtype=np.float64)
        if abs(out[2]) < 1e-9:
            raise ValueError("degenerate homography: w ~= 0")
        return float(out[0] / out[2]), float(out[1] / out[2])

    @property
    def is_identity_like(self) -> bool:
        """True when no calibration has been applied (unit pixel mapping)."""
        return bool(np.allclose(self.matrix, np.eye(3), atol=1e-9))


def cv2_find_homography(src: np.ndarray, dst: np.ndarray) -> tuple[np.ndarray | None, np.ndarray]:
    """Tiny indirection so :meth:`Homography.from_corners` doesn't import cv2
    at module load time.  Falls back to a pure-numpy DLT solver when cv2 is
    not installed (e.g. headless CI)."""
    try:
        import cv2

        H, mask = cv2.findHomography(src, dst, method=0)
        return H, np.zeros((len(src), 1), dtype=np.uint8) if mask is None else mask
    except ImportError:
        return _dlt_homography(src, dst), np.ones((len(src), 1), dtype=np.uint8)


def _dlt_homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Pure-numpy Direct Linear Transform for a 2D homography."""
    n = src.shape[0]
    if n < 4:
        return np.eye(3, dtype=np.float64)
    a: list[list[float]] = []
    for (x, y), (u, v) in zip(src, dst, strict=False):
        a.append([-x, -y, -1.0, 0.0, 0.0, 0.0, u * x, u * y, u])
        a.append([0.0, 0.0, 0.0, -x, -y, -1.0, v * x, v * y, v])
    A = np.asarray(a, dtype=np.float64)
    _, _, vh = np.linalg.svd(A)
    H = vh[-1].reshape(3, 3)
    if abs(H[2, 2]) > 1e-12:
        H = H / H[2, 2]
    return np.asarray(H, dtype=np.float64)


def identity_homography() -> Homography:
    """A 1:1 mapping (useful as a no-op when calibration is unavailable)."""
    return Homography(matrix=np.eye(3, dtype=np.float64))
