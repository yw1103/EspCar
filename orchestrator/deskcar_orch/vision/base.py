"""Abstract frame source used by every vision module.

Splitting this from :mod:`camera` lets tests inject synthetic frames (a
numpy array plus a synthetic pose) without ever opening a VideoCapture.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from deskcar_orch.geometry import Pose


@dataclass(frozen=True)
class Frame:
    """One captured frame + the car pose estimated for it (if any)."""

    image: np.ndarray
    timestamp_s: float
    pose: Pose | None = None


@runtime_checkable
class FrameSource(Protocol):
    """Anything that can hand out a stream of :class:`Frame`."""

    def open(self) -> None: ...
    def close(self) -> None: ...
    def frames(self) -> Iterator[Frame]: ...
    @property
    def size(self) -> tuple[int, int]: ...


# Alias kept for documentation / type hints.
Camera = FrameSource