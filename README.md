# DeskCar 桌面级两轮智能小车

v1 是 Wi-Fi 遥控玩具车；v2 新增 USB 摄像头视觉闭环、Qi 无线充电、5 针磁吸扩展口，以及主机端带类型注解的 Python SDK。

## 项目内容

| 目录 | 作用 |
| :--- | :--- |
| `firmware/`     | ESP32 Arduino / PlatformIO 固件（可直接构建） |
| `sdk/`          | `deskcar` Python SDK（异步、带类型、可 `pip install`） |
| `orchestrator/` | 主机端视觉 + 自动回冲 + 避障 |
| `hardware/`     | KiCad 原理图、PCB、BOM、机械图 |
| `docs/`         | 通信协议、SDK 参考、标定说明、硬件笔记 |
| `examples/`     | 可直接跑的示例脚本 |

## 快速上手

```bash
# 1. 安装 SDK
pip install -e ./sdk

# 2. 烧录固件（一次性）
pio run -d firmware -t upload

# 3. 首次直连小车 AP，确认状态
python examples/read_state_demo.py --host 192.168.4.1
```

小车首次上电会创建名为 `ESP32_Car_Control` 的开放热点。先临时连上它，给小车写入
2.4 GHz Wi-Fi 凭据；重启后小车优先加入用户局域网，电脑可以保持正常上网，并用
`Chassis.discover_first()` 或 `python examples/read_state_demo.py` 自动发现小车。

```python
from deskcar import Chassis

car = Chassis.from_host("192.168.4.1")
# await car.connect()
# await car.configure_wifi("你的WiFi名称", "你的WiFi密码")
```

如果 STA 连接失败，小车会继续保留 `ESP32_Car_Control` 作为兜底配网入口。

## 已锁定的设计决策

- 视觉由主机 PC 通过 USB 摄像头完成
- 充电：Qi 5W 无线充电（车端 1S 锂电 1000 mAh）
- 扩展口：5 针 pogo（3.3V / GND / SDA / SCL / INT）+ 4 颗 N52 磁铁
- 定位：车顶 ArUco + 充电坞 AprilTag（双源）
- SDK：Python 优先、带类型注解，协议见 `docs/PROTOCOL.md`

完整规划与权衡见 [PROJECT_PLAN.md](PROJECT_PLAN.md)。

## 自动回冲

要启用自动回冲，请看 [orchestrator/README.md](orchestrator/README.md)、
[硬件说明](docs/HARDWARE.md) 与 [标定说明](docs/CALIBRATION.md)。
一步步的实操流程见 [docs/实操说明.md](docs/实操说明.md)。

## 许可证

MIT
