"""OpenCV VideoCapture wrapper, exposed as a :class:`FrameSource`."""
from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

import numpy as np

from deskcar_orch.vision.base import Frame, FrameSource

_LOG = logging.getLogger(__name__)


class OpenCVCamera(FrameSource):
    """One USB camera, blocking ``read()`` wrapped in a generator.

    Tested with Logitech C270 and ELP 1080p modules.  Anything that
    V4L2 can hand to OpenCV should work out of the box.
    """

    def __init__(
        self,
        device: int = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        flip_vertical: bool = False,
    ) -> None:
        self._device = device
        self._width = width
        self._height = height
        self._fps = fps
        self._flip_vertical = flip_vertical
        self._cap: Any | None = None

    def open(self) -> None:
        import cv2  # local import: keeps the rest of the package OpenCV-free

        cap = cv2.VideoCapture(self._device)
        if not cap.isOpened():
            raise RuntimeError(f"failed to open camera device {self._device}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        cap.set(cv2.CAP_PROP_FPS, float(self._fps))
        self._cap = cap
        _LOG.info("camera %d open: %dx%d @ %d fps",
                  self._device, self._width, self._height, self._fps)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def frames(self) -> Iterator[Frame]:
        if self._cap is None:
            raise RuntimeError("camera not opened; call open() first")
        cap = self._cap
        while True:
            ok, image = cap.read()
            if not ok:
                _LOG.warning("camera read failed; bailing out of stream")
                return
            if self._flip_vertical:
                image = np.flipud(image)
            yield Frame(image=image, timestamp_s=time.monotonic())

    @property
    def size(self) -> tuple[int, int]:
        return (self._width, self._height)
