# DeskCar Orchestrator

PC-side vision + auto-dock loop for the DeskCar desktop smart chassis.

## What it does

* 通过 USB 摄像头识别车顶 ArUco 标记，实时估计小车在桌面上的位姿。
* 通过 AprilTag 识别充电仓位置，引导小车自动回充。
* 当固件报告电量低于阈值（默认 20%）时自动触发回充。
* 回充完成后停在充电仓内，直到收到退出指令。

## Quick start

```bash
cd orchestrator
pip install -e ".[dev]"

# 标定相机单应矩阵（只需一次）
python scripts/calibrate_homography.py --width 1.4 --height 0.8 --camera 0

# 启动自动回充
python -m deskcar_orch -c configs/default.yaml

# 强制立即回充（调试用）
python -m deskcar_orch -c configs/default.yaml --dock
```

## Project layout

```text
deskcar_orch/
├── bridge/          # 与 ESP32 固件通信的薄封装
├── controller/      # 视觉伺服 P 控制器
├── planning/        # 回充状态机
├── vision/          # 相机、ArUco/AprilTag、单应矩阵
├── calib/           # 标定结果（运行时自动生成）
└── geometry.py      # 2D 姿态/速度/向量工具
```

## Configuration

默认配置在 `configs/default.yaml`。关键字段：

* `car_host`：ESP32 AP 的 IP（默认 `192.168.4.1`）。
* `vision.car_marker_id` / `vision.dock_tag_id`：ArUco / AprilTag ID。
* `charger.dock_pad_offset_m`：tag 中心到 pad 中心偏移，打印后需实测。
* `charger.dock_pad_stand_off_m`：视觉伺服停车距离，按线圈耦合距离调整。

详见 `../docs/CALIBRATION.md`。

## Tests

```bash
cd orchestrator
PYTHONPATH=. pytest -q
ruff check deskcar_orch tests
mypy deskcar_orch --no-incremental
```

## Hardware

充电仓 3D 打印方案、车体改动、BOM 见 `../docs/HARDWARE.md`。
