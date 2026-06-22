"""Bridge layer: thin adapters over the deskcar SDK and the camera."""
from __future__ import annotations

from deskcar_orch.bridge.ws_client import WsCar

__all__ = ["WsCar"]