# DeskCar 标定指南

本指南只需要做一次：装好摄像头、打印好充电仓后，标定摄像头到桌面的单应矩阵，并测量 tag 到 pad 的实际偏移。

## 1. 标定前的准备

* 摄像头已经固定，能完整俯视小车工作桌面。
* 桌面上已用尺子量出 4 个角点的实际坐标（单位：米）。
* 小车和充电仓已按 `./HARDWARE.md` 装配。
* 已安装 orchestrator 依赖：

```bash
cd orchestrator
pip install -e ".[dev]"
```

## 2. 相机单应矩阵标定

运行交互式标定脚本：

```bash
cd orchestrator
python scripts/calibrate_homography.py --width 1.4 --height 0.8 --camera 0
```

按顺序点击画面中桌面的 4 个角：

1. 左上角（对应世界坐标 `(0, 0)`）
2. 右上角（对应世界坐标 `(width, 0)`）
3. 右下角（对应世界坐标 `(width, height)`）
4. 左下角（对应世界坐标 `(0, height)`）

脚本会生成：

```text
orchestrator/deskcar_orch/calib/homography.npy
```

运行时被 `runtime.py::_load_homography_or_identity()` 自动加载。

### 2.1 没有 OpenCV 时的替代方法

如果你只需要验证数学，可以用纯 numpy DLT：

```python
import numpy as np
from deskcar_orch.vision.homography import Homography

pixel = [(100, 80), (600, 80), (600, 400), (100, 400)]
world = [(0.0, 0.0), (1.4, 0.0), (1.4, 0.8), (0.0, 0.8)]
H = Homography.from_corners(pixel, world)
np.save("orchestrator/deskcar_orch/calib/homography.npy", H.matrix)
```

## 3. 验证单应矩阵

标定后，把车放在桌面已知位置，运行：

```bash
python -m deskcar_orch -c configs/default.yaml --dock
```

如果视觉正常，日志里会显示小车坐标；把车推到 `(0,0)` 附近，坐标应接近 `(0,0)`。

## 4. 测量 `dock_pad_offset_m`

`configs/default.yaml` 中默认：

```yaml
charger:
  dock_pad_offset_m: [0.04, 0.0]
```

含义：从 **tag 中心** 沿 tag 朝向走 `40 mm` 到达 **pad 中心**。

测量步骤：

1. 用尺子量 tag 中心到 pad 中心的直线距离 `d`。
2. 确认 tag 上边缘朝向 pad（见 `./HARDWARE.md` 第 2 节）。
3. 如果 tag 正好在 pad 正左方且上边缘朝 pad，则填入 `[d, 0.0]`。
4. 如果 tag 装在 pad 正前方，则偏移主要在 y 方向，例如 `[0.0, 0.04]`。

## 5. 测量/调整 `dock_pad_stand_off_m`

默认值 `0.08`（80 mm）表示视觉伺服把车停在 pad 面前 8 cm 处，之后小车以 `couple_linear_mps` 蠕动前进，直到 RX 线圈耦合。

* 如果你的 RX/TX 线圈耦合距离较短，可以减小到 `0.05`。
* 如果你的小车刹车惯性大，可以增大到 `0.12`。

## 6. 标定检查清单

* [ ] `homography.npy` 已生成并保存在 `orchestrator/deskcar_orch/calib/`
* [ ] 把车放在桌面 4 个已知点，视觉坐标与尺子误差 `< 2 cm`
* [ ] `dock_pad_offset_m` 已按实际打印件测量
* [ ] `dock_pad_stand_off_m` 已按线圈耦合距离调整
* [ ] 修改后的配置已保存为 `configs/default.yaml` 或副本
