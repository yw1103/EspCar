"""AprilTag (tag36h11) dock detector on the desk surface."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from deskcar_orch.geometry import Pose
from deskcar_orch.vision.homography import Homography

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class DockObservation:
    """One successful dock tag detection."""

    pose: Pose
    pixel: tuple[float, float]
    tag_id: int


class AprilTagDockDetector:
    """Detect the charging dock via a tag36h11 AprilTag on its top face.

    OpenCV 4.7+ unifies ArUco and AprilTag under ``cv2.aruco``; we still
    import the legacy constants for older OpenCV builds.
    """

    def __init__(
        self,
        homography: Homography,
        *,
        tag_id: int = 0,
        tag_size_mm: float = 60.0,
    ) -> None:
        self._homography = homography
        self._tag_id = tag_id
        self._tag_size_mm = tag_size_mm
        self._detector: Any = None
        self._dict: Any = None

    def _ensure_loaded(self) -> None:
        if self._detector is not None:
            return
        import cv2  # type: ignore[import-not-found]

        # tag36h11 is the AprilTag default family used by apriltag ROS nodes.
        try:
            self._dict = cv2.aruco.getPredefinedDictionary(
                cv2.aruco.DICT_APRILTAG_36h11
            )
        except AttributeError:  # very old OpenCV
            raise RuntimeError("OpenCV build lacks APRILTAG_36h11; need 4.7+")
        params = cv2.aruco.DetectorParameters()
        self._detector = cv2.aruco.ArucoDetector(self._dict, params)

    def detect(self, image: np.ndarray) -> DockObservation | None:
        """Return the dock pose in world frame, or None if not seen."""
        self._ensure_loaded()
        import cv2  # type: ignore[import-not-found]

        corners, ids, _ = self._detector.detectMarkers(image)
        if ids is None:
            return None
        for marker_corners, marker_id in zip(corners, ids.flatten().tolist()):
            if marker_id != self._tag_id:
                continue
            pts = marker_corners.reshape(4, 2)
            center = pts.mean(axis=0)
            world = self._homography.pixel_to_world(float(center[0]), float(center[1]))
            top_mid = (pts[0] + pts[1]) / 2
            bot_mid = (pts[2] + pts[3]) / 2
            forward = top_mid - bot_mid
            angle = float(np.arctan2(forward[1], forward[0]))
            return DockObservation(
                pose=Pose(world.x, world.y, angle),
                pixel=(float(center[0]), float(center[1])),
                tag_id=marker_id,
            )
        return None