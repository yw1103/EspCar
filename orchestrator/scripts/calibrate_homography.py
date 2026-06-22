"""Interactive camera-to-desk homography calibration.

Usage::

    cd orchestrator
    python scripts/calibrate_homography.py --width 1.4 --height 0.8

Click the four desk corners in this order:
    1. top-left     -> world (0, 0)
    2. top-right    -> world (width, 0)
    3. bottom-right -> world (width, height)
    4. bottom-left  -> world (0, height)

The resulting 3x3 matrix is saved to ``deskcar_orch/calib/homography.npy``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--camera", type=int, default=0, help="OpenCV camera device index")
    p.add_argument("--width", type=float, default=1.4, help="desk width in metres (X)")
    p.add_argument("--height", type=float, default=0.8, help="desk depth in metres (Y)")
    p.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "deskcar_orch" / "calib" / "homography.npy",
        help="where to save the homography matrix",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"failed to open camera {args.camera}", file=sys.stderr)
        return 1

    # Use a resolution close to the orchestrator config for consistent scaling.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    clicks: list[tuple[int, int]] = []
    world_pts = [
        (0.0, 0.0),
        (args.width, 0.0),
        (args.width, args.height),
        (0.0, args.height),
    ]

    def _on_mouse(event: int, x: int, y: int, _flags: int, _param: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(clicks) < 4:
            clicks.append((x, y))

    cv2.namedWindow("calibrate")
    cv2.setMouseCallback("calibrate", _on_mouse)

    print("Click the 4 desk corners in order: TL, TR, BR, BL")
    while len(clicks) < 4:
        ok, frame = cap.read()
        if not ok:
            continue
        for i, (x, y) in enumerate(clicks):
            cv2.circle(frame, (x, y), 6, (0, 0, 255), -1)
            cv2.putText(frame, str(i + 1), (x + 8, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("calibrate", frame)
        if cv2.waitKey(30) & 0xFF == 27:
            cap.release()
            cv2.destroyAllWindows()
            return 0

    cap.release()
    cv2.destroyAllWindows()

    src = np.asarray(clicks, dtype=np.float64)
    dst = np.asarray(world_pts, dtype=np.float64)
    H, _ = cv2.findHomography(src, dst)
    if H is None:
        print("cv2.findHomography failed; points may be collinear", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output, H)
    print(f"saved homography to {args.output}")
    print(H)
    return 0


if __name__ == "__main__":
    sys.exit(main())
