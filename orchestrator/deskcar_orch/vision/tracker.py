"""Car-top ArUco marker tracker -> world-frame pose."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, ClassVar

import numpy as np

from deskcar_orch.geometry import Pose
from deskcar_orch.vision.homography import Homography

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarkerObservation:
    """One successful marker detection."""

    pose: Pose
    pixel: tuple[float, float]
    marker_id: int


class ArUcoTracker:
    """Detect the car-top 4x4 ArUco marker, return a world-frame pose.

    The marker's *center* is mapped through the floor homography to a
    world point; the heading is the marker's rotation about its
    centre, also expressed in the world frame.
    """

    _DICT_NAMES: ClassVar[dict[str, str]] = {
        "DICT_4X4_50": "DICT_4X4_50",
        "DICT_4X4_100": "DICT_4X4_100",
        "DICT_5X5_50": "DICT_5X5_50",
        "DICT_6X6_50": "DICT_6X6_50",
        "DICT_ARUCO_ORIGINAL": "DICT_ARUCO_ORIGINAL",
    }

    def __init__(
        self,
        homography: Homography,
        *,
        marker_id: int = 0,
        dictionary: str = "DICT_4X4_50",
        marker_size_mm: float = 32.0,
    ) -> None:
        self._homography = homography
        self._marker_id = marker_id
        self._dict_name = dictionary
        self._marker_size_mm = marker_size_mm
        self._detector: Any = None
        self._dict: Any = None

    def _ensure_loaded(self) -> None:
        if self._detector is not None:
            return
        import cv2

        dict_const = getattr(cv2.aruco, self._dict_name, None)
        if dict_const is None:
            raise ValueError(f"unknown ArUco dictionary: {self._dict_name}")
        self._dict = cv2.aruco.getPredefinedDictionary(dict_const)
        params = cv2.aruco.DetectorParameters()
        # OpenCV 4.7+ unified detector API.
        self._detector = cv2.aruco.ArucoDetector(self._dict, params)

    def track(self, image: np.ndarray) -> MarkerObservation | None:
        """Return the car pose in world frame, or None if not seen."""
        self._ensure_loaded()

        corners, ids, _ = self._detector.detectMarkers(image)
        if ids is None:
            return None
        for marker_corners, marker_id in zip(corners, ids.flatten().tolist(), strict=False):
            if marker_id != self._marker_id:
                continue
            pts = marker_corners.reshape(4, 2)
            center = pts.mean(axis=0)
            world = self._homography.pixel_to_world(float(center[0]), float(center[1]))
            # Heading: the marker's "up" axis is the top edge in pixel coords.
            top_mid = (pts[0] + pts[1]) / 2
            bot_mid = (pts[2] + pts[3]) / 2
            forward_pixel = top_mid - bot_mid
            angle = float(np.arctan2(forward_pixel[1], forward_pixel[0]))
            return MarkerObservation(
                pose=Pose(world.x, world.y, angle),
                pixel=(float(center[0]), float(center[1])),
                marker_id=marker_id,
            )
        return None
