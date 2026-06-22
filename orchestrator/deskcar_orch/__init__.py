"""DeskCar PC orchestrator.

A small, typed Python package that turns a USB camera + a DeskCar chassis
into a self-docking, obstacle-aware desktop robot.  Heavy vision deps
(OpenCV / ArUco) live behind lazy imports so the pure-python control
logic stays testable on a headless box.
"""
from __future__ import annotations

from deskcar_orch.config import OrchestratorConfig
from deskcar_orch.geometry import Pose, Twist, Vec2

__all__ = ["OrchestratorConfig", "Pose", "Twist", "Vec2"]
__version__ = "0.1.0"