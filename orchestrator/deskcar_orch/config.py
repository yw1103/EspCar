"""Runtime configuration loader for the orchestrator.

A single dataclass tree plus a YAML loader.  The CLI builds its config
from ``configs/default.yaml`` and overrides individual fields without
ever reaching for ``argparse`` magic.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml  # PyYAML is a required dep of the orchestrator


@dataclass(frozen=True)
class CameraConfig:
    device: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    flip_vertical: bool = False


@dataclass(frozen=True)
class VisionConfig:
    aruco_dict: str = "DICT_4X4_50"
    car_marker_id: int = 0
    car_marker_size_mm: float = 32.0
    dock_tag_family: str = "tag36h11"
    dock_tag_id: int = 0
    dock_tag_size_mm: float = 60.0
    obstacle_min_area_px: int = 1500
    obstacle_history: int = 8


@dataclass(frozen=True)
class ServoConfig:
    kp_linear: float = 0.8
    kp_angular: float = 2.5
    max_linear_mps: float = 0.30
    max_angular_rps: float = 1.6
    goal_tolerance_m: float = 0.05
    goal_tolerance_rad: float = 0.20
    loop_hz: float = 30.0


@dataclass(frozen=True)
class ChargerConfig:
    seek_max_seconds: float = 90.0
    align_tolerance_m: float = 0.06
    couple_timeout_s: float = 30.0
    full_current_ma: float = 50.0
    # AprilTag is on a side board, NOT on the pad itself (see HARDWARE.md).
    # Offset from tag CENTRE to pad CENTRE in the tag's body frame
    # (+x forward, +y left).  Calibrate once after printing the dock.
    dock_pad_offset_m: tuple[float, float] = (0.04, 0.0)
    # How far back from the pad face the car stops, in metres.
    dock_pad_stand_off_m: float = 0.08

    # Battery threshold that triggers auto-dock (%).
    dock_soc_threshold: float = 20.0
    # Creep speed used in the final COUPLE phase (m/s).
    couple_linear_mps: float = 0.06
    # Minimum time the charge signal must be active before we trust it (s).
    couple_settle_s: float = 2.0
    # How far the car backs away during UNDOCK (m).
    undock_distance_m: float = 0.20
    # Back-up speed during UNDOCK (m/s, positive scalar).
    undock_linear_mps: float = 0.10
    # Safety cap for the UNDOCK back-up phase (s).
    undock_timeout_s: float = 3.0


@dataclass(frozen=True)
class OrchestratorConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    servo: ServoConfig = field(default_factory=ServoConfig)
    charger: ChargerConfig = field(default_factory=ChargerConfig)
    car_host: str = "192.168.4.1"
    desk_size_m: tuple[float, float] = (1.4, 0.8)
    log_level: str = "INFO"

    def with_overrides(self, **kwargs: Any) -> "OrchestratorConfig":
        """Return a copy with the given top-level fields replaced."""
        return replace(self, **kwargs)


def load_config(path: str | Path | None = None) -> OrchestratorConfig:
    """Load a config from YAML; return defaults if the file is absent."""
    if path is None:
        return OrchestratorConfig()
    p = Path(path)
    if not p.exists():
        return OrchestratorConfig()
    with p.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}
    return _from_dict(raw)


def _from_dict(raw: dict[str, Any]) -> OrchestratorConfig:
    def section(name: str, factory: type, attrs: dict[str, Any]) -> Any:
        merged = dict(raw.get(name, {}) or {})
        merged.update(attrs)
        return factory(**merged)

    charger_overrides: dict[str, Any] = {}
    raw_charger = raw.get("charger", {})
    if "dock_pad_offset_m" in raw_charger:
        charger_overrides["dock_pad_offset_m"] = tuple(
            raw_charger["dock_pad_offset_m"]
        )  # type: ignore[arg-type]

    return OrchestratorConfig(
        camera=section("camera", CameraConfig, {}),
        vision=section("vision", VisionConfig, {}),
        servo=section("servo", ServoConfig, {}),
        charger=section("charger", ChargerConfig, charger_overrides),
        car_host=str(raw.get("car_host", "192.168.4.1")),
        desk_size_m=tuple(raw.get("desk_size_m", (1.4, 0.8))),  # type: ignore[arg-type]
        log_level=str(raw.get("log_level", "INFO")),
    )
