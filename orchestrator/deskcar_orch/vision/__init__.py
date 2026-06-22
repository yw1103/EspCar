"""Vision subsystem.

Heavy modules (camera, tracker, dock, obstacles) import OpenCV lazily so
unit tests can exercise :mod:`homography` and :mod:`controller` on a
headless box.
"""
from __future__ import annotations

from deskcar_orch.vision.base import Camera, Frame, FrameSource

__all__ = ["Camera", "Frame", "FrameSource"]