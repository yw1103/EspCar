"""Homography tests that do NOT require OpenCV at import time."""
from __future__ import annotations

import numpy as np
import pytest

from deskcar_orch.vision.homography import Homography, _dlt_homography, identity_homography


def test_identity_homography_is_pure_passthrough() -> None:
    H = identity_homography()
    p = H.pixel_to_world(120.0, 80.0)
    assert p.x == pytest.approx(120.0)
    assert p.y == pytest.approx(80.0)
    u, v = H.world_to_pixel(p)
    assert u == pytest.approx(120.0)
    assert v == pytest.approx(80.0)


def test_pure_numpy_dlt_recovers_identity_for_trivial_corners() -> None:
    # When pixel coords and world coords are identical, the homography
    # should be the identity (up to scale).
    src = np.array([[0, 0], [100, 0], [100, 50], [0, 50]], dtype=np.float64)
    dst = src.copy()
    H = _dlt_homography(src, dst)
    assert H.shape == (3, 3)
    normalised = H / H[2, 2]
    assert np.allclose(normalised, np.eye(3), atol=1e-6)


def test_pure_numpy_dlt_handles_small_affine_warp() -> None:
    # Translate + scale: world = 2 * pixel + (10, 5)
    src = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
    dst = np.array([[10, 5], [30, 5], [30, 25], [10, 25]], dtype=np.float64)
    H = _dlt_homography(src, dst)
    normalised = H / H[2, 2]
    # (0, 0) -> (10, 5)
    out = normalised @ np.array([0, 0, 1.0], dtype=np.float64)
    assert out[0] / out[2] == pytest.approx(10.0, abs=1e-6)
    assert out[1] / out[2] == pytest.approx(5.0, abs=1e-6)
    # (10, 0) -> (30, 5)
    out = normalised @ np.array([10, 0, 1.0], dtype=np.float64)
    assert out[0] / out[2] == pytest.approx(30.0, abs=1e-6)
    assert out[1] / out[2] == pytest.approx(5.0, abs=1e-6)


def test_homography_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError):
        Homography(matrix=np.eye(4))


def test_pixel_to_world_degenerate_w_raises() -> None:
    # A homography whose last row sums to 0 maps every pixel to infinity.
    H = Homography(matrix=np.array([[1, 0, 0], [0, 1, 0], [0, 0, 0]], dtype=np.float64))
    with pytest.raises(ValueError):
        H.pixel_to_world(1.0, 1.0)