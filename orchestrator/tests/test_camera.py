"""Tests for USB camera warmup."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from deskcar_orch.vision.camera import OpenCVCamera


def test_wait_ready_accepts_consecutive_frames() -> None:
    cam = OpenCVCamera(warmup_timeout_s=1.0, warmup_min_frames=2)
    cam._cap = MagicMock()
    good = np.zeros((480, 640, 3), dtype=np.uint8)
    cam._cap.read.side_effect = [
        (False, None),
        (True, good),
        (True, good),
    ]
    cam.wait_ready()
    assert cam._cap.read.call_count == 3


def test_wait_ready_times_out() -> None:
    cam = OpenCVCamera(warmup_timeout_s=0.2, warmup_min_frames=2)
    cam._cap = MagicMock()
    cam._cap.read.return_value = (False, None)
    with pytest.raises(RuntimeError, match="did not become ready"):
        cam.wait_ready()
