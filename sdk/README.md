# deskcar — DeskCar 桌面小车的 Python SDK

异步、带类型注解、不依赖 OpenCV 的 DeskCar ESP32 客户端。说的是跟
`firmware/src/server.cpp` 一样的 JSON-over-WebSocket 协议；完整线协议见
`docs/PROTOCOL.md`。

## 安装

```bash
pip install deskcar
# 或从本仓库可编辑安装：
pip install -e "./sdk[dev]"
```

## 快速开始

```python
import asyncio
from deskcar import Chassis, StateSnapshot

async def main() -> None:
    car = await Chassis.discover_first()       # UDP 局域网扫描
    await car.connect()                        # 打开 WS + HTTP

    # 响应式控制：每个轮子带符号的 PWM，范围 [-255, 255]
    await car.drive(left=120, right=120)
    await asyncio.sleep(1.0)
    await car.stop()

    # 读取最新一次遥测快照
    snap: StateSnapshot = await car.read_state()
    print(snap.charge.name, snap.v, snap.soc)

    # 列出磁吸扩展口上的设备
    devices = await car.scan_expansion()       # 强制做一次 I2C 扫描
    print([d.address for d in devices])

    # 以约 5 Hz 的频率持续接收 state 帧，直到被取消
    async for ev in car.events():
        if isinstance(ev, StateSnapshot):
            print("ts", ev.ts, "v", ev.v)

asyncio.run(main())
```

## SDK 提供的接口

| 方法 | 作用 |
| :--- | :--- |
| `Chassis.discover(timeout)`        | UDP 扫描局域网，返回听到的所有小车 |
| `Chassis.discover_first(timeout)`  | 听到的第一台车；若超时则抛 `DeskCarTimeoutError` |
| `Chassis.from_host("1.2.3.4")`     | 跳过发现阶段，直接连指定 IP |
| `Chassis.connect()` / `close()`    | 打开 / 关闭 WS + HTTP |
| `Chassis.drive(left, right)`       | 每个轮子的 PWM，范围 -255..255 |
| `Chassis.stop()`                   | 硬刹车 |
| `Chassis.set_speed_cap(value)`     | 全局 PWM 上限 0..255（固件会持久化） |
| `Chassis.scan_expansion()`         | 返回磁吸扩展口上的 I2C 设备 |
| `Chassis.read_state()`             | 一次性读取遥测快照 |
| `Chassis.events()`                 | WS 事件流（state + 扩展口事件） |

SDK 本身**不**做路径规划、不做自动回冲、不闭合控制环——这些都在 PC 端的
`orchestrator/` 包里，它订阅同一份事件流，发送 `drive` / `stop` 这种响应式命令。

## 开发

```bash
pip install -e "./sdk[dev]"
pytest
ruff check src/deskcar tests
mypy src/deskcar --no-incremental
```

## 许可证

MIT
