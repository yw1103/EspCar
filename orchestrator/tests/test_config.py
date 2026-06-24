"""Tests for the YAML config loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from deskcar_orch.config import OrchestratorConfig, load_config


def test_defaults_when_path_is_none() -> None:
    cfg = load_config(None)
    assert isinstance(cfg, OrchestratorConfig)
    assert cfg.car_host == "192.168.4.1"
    assert cfg.charger.dock_pad_offset_m == (0.04, 0.0)
    assert cfg.charger.dock_pad_stand_off_m == pytest.approx(0.08)


def test_missing_file_returns_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "nope.yaml")
    assert cfg.car_host == "192.168.4.1"


def test_loads_real_default_yaml() -> None:
    cfg = load_config("configs/default.yaml")
    assert cfg.servo.kp_linear == pytest.approx(0.8)
    assert cfg.charger.dock_pad_offset_m == (0.04, 0.0)


def test_with_overrides_replaces_top_level_field() -> None:
    cfg = OrchestratorConfig()
    new = cfg.with_overrides(car_host="10.0.0.5")
    assert new.car_host == "10.0.0.5"
    assert cfg.car_host == "192.168.4.1"  # original untouched


def test_default_yaml_loads_charger_timing_fields() -> None:
    cfg = load_config("configs/default.yaml")
    assert cfg.charger.dock_soc_threshold == pytest.approx(20.0)
    assert cfg.charger.couple_linear_mps == pytest.approx(0.06)
    assert cfg.charger.couple_settle_s == pytest.approx(2.0)
    assert cfg.charger.undock_distance_m == pytest.approx(0.20)
    assert cfg.charger.undock_linear_mps == pytest.approx(0.10)


def test_default_yaml_apriltag_ids_and_camera_warmup() -> None:
    cfg = load_config("configs/default.yaml")
    assert cfg.vision.aruco_dict == "DICT_APRILTAG_36h11"
    assert cfg.vision.car_marker_id == 3
    assert cfg.vision.car_marker_size_mm == pytest.approx(50.0)
    assert cfg.vision.dock_tag_id == 2
    assert cfg.vision.dock_tag_size_mm == pytest.approx(50.0)
    assert cfg.camera.warmup_timeout_s == pytest.approx(20.0)
    assert cfg.camera.warmup_min_frames == 5
