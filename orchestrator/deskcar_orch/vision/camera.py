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
        *,
        warmup_timeout_s: float = 15.0,
        warmup_min_frames: int = 3,
    ) -> None:
        self._device = device
        self._width = width
        self._height = height
        self._fps = fps
        self._flip_vertical = flip_vertical
        self._warmup_timeout_s = warmup_timeout_s
        self._warmup_min_frames = warmup_min_frames
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

    def wait_ready(self) -> None:
        """Block until the camera delivers consecutive valid frames.

        ``VideoCapture.isOpened()`` can succeed while the first few
        ``read()`` calls still fail on slow external USB modules.  The
        orchestrator calls this before connecting to the car so motors
        do not move blind.
        """
        if self._cap is None:
            raise RuntimeError("camera not opened; call open() first")
        cap = self._cap
        deadline = time.monotonic() + self._warmup_timeout_s
        consecutive = 0
        _LOG.info(
            "waiting for camera %d (%d good frames, timeout %.1f s)",
            self._device,
            self._warmup_min_frames,
            self._warmup_timeout_s,
        )
        while time.monotonic() < deadline:
            ok, image = cap.read()
            if ok and image is not None and image.size > 0:
                consecutive += 1
                if consecutive >= self._warmup_min_frames:
                    _LOG.info("camera %d ready after %d frame(s)",
                              self._device, consecutive)
                    return
            else:
                consecutive = 0
            time.sleep(0.05)
        raise RuntimeError(
            f"camera {self._device} did not become ready within "
            f"{self._warmup_timeout_s:.1f} s"
        )

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
