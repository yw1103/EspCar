# deskcar SDK 参考手册

`deskcar` 全部公开符号的完整参考。基于 `sdk/src/deskcar/__init__.py` 和
`sdk/tests/test_wire_shape.py`（后者是固件实际发出什么的真相来源）生成。

## 顶层导出

```python
from deskcar import (
    Chassis,            # 高级客户端
    ChassisInfo,        # 发现结果
    StateSnapshot,      # 解析后的 state 帧
    ExpansionDevice,    # 磁吸扩展口上的一个 I2C 设备
    ChargeState,        # 枚举：idle / detected / charging / full / fault
    DeskCarError,       # 基础异常
    DeskCarTimeoutError,
    NotConnectedError,
    ProtocolError,
    TransportError,
)
```

---

## `Chassis`

异步、带类型的高级客户端。可以当 async context manager 用，也可以自己
显式调 `connect()` / `close()`。

```python
async with await Chassis.discover_first() as car:
    await car.drive(120, 120)
```

### 构造方法

#### `Chassis.discover(timeout=2.0) -> list[Chassis]`

广播一条 UDP 发现包，返回截止时间内听到的所有 `Chassis`。

#### `Chassis.discover_first(timeout=2.0) -> Chassis`

同上，但只返回第一台；超时则抛 `DeskCarTimeoutError`。

#### `Chassis.from_host(host: str, *, port: int = 80) -> Chassis`

跳过发现阶段，直接连已知 IP。在 CI 或者固定布线桌面上用很方便。

### 生命周期

| 方法 | 备注 |
| :--- | :--- |
| `await car.connect()` | 打开 WS + HTTP 会话 |
| `await car.close()`   | 关闭；调两次也安全 |
| `async with await Chassis.discover_first() as car: ...` | 一行的简写 |
| `car.info` | 当前绑定的 `ChassisInfo` |

### 响应式控制

| 方法 | 作用 | 线协议 |
| :--- | :--- | :--- |
| `await car.drive(left: int, right: int)` | 每轮 PWM，-255..255 | `{"type":"drive","left":..,"right":..}` |
| `await car.stop()`                    | 硬刹车（用 `ledcWrite(0)`） | `{"type":"stop"}` |
| `await car.set_speed_cap(value: int)` | 全局 PWM 上限 0..255        | `{"type":"set_speed","value":..}` |

`drive` **不**会阻塞——它就是一条 WS 帧。如果你要让电机一直转，最多每
200 ms 发一次 `drive`；这是固件 `loop()` 广播 state 的频率，超过这个
间隔 WS 一旦断开就会隐式发 `stop`。

### 自省

| 方法 | 作用 |
| :--- | :--- |
| `await car.scan_expansion() -> list[ExpansionDevice]` | 强制做一次 I2C 扫描，返回设备列表 |
| `await car.read_state() -> StateSnapshot` | 一次性读取遥测帧（走 HTTP） |
| `car.feed(payload)` | 测试钩子：把一帧原始数据塞进接收队列 |

### 事件流

```python
async for ev in car.events():
    if isinstance(ev, StateSnapshot):
        ...   # 类型化访问
    else:
        ...   # 原始 dict：device_attached / error / encoder 等
```

`events()` 是一个永不结束的异步迭代器，可安全取消：WS 断了之后迭代结束，
下一次 `connect()` 会开新的流。

`connect()` 会自动启动后台 reader，持续消费固件广播，防止只发命令不读事件时把
ESP32 的 TCP 窗口堵满。`events()` 只是把 SDK 内部已接收的帧再交给上层。

SDK **不**做半帧阻塞；底层 transport 会自己拼 WS 消息。

---

## `ChassisInfo`

发现阶段返回的不可变 pydantic 模型。

```python
info = ChassisInfo(host="192.168.4.1", port=80, name="deskcar-7c9e")
info.base_url   # "http://192.168.4.1:80"
info.ws_url     # "ws://192.168.4.1:80/api/v1/stream"
```

| 字段 | 类型 | 含义 |
| :--- | :--- | :--- |
| `host` | str | IP 地址 |
| `port` | int | TCP 端口，默认 80 |
| `name` | str \| None | 宣告里的人可读名字 |
| `mac` | str \| None | 小车 MAC（如果宣告里有） |
| `firmware_version` | int \| None | 协议版本，见 `firmware/include/protocol.h` |

---

## `StateSnapshot`

`read_state()` 和每一次 WS 的 `state` 事件解析完都是这个形状。除了
`type`、`ts`、`charge` 之外其他字段都可以缺省，所以新出厂的车（INA219
还没采到数）也能正常解析。

```python
class StateSnapshot(BaseModel):
    type: Literal["state"] = "state"
    ts: int                              # 距上电的毫秒
    v: float | None = None               # V
    i: float | None = None               # mA
    soc: float | None = None             # %
    charge: ChargeState = ChargeState.IDLE
    wifi: str | None = None              # "AP" / "STA" / "AP+STA"
    speed: int | None = None             # 0..255
    exp: list[ExpansionDevice] = []      # 磁吸扩展口 I2C 设备，不含板载 INA219
```

未知字段会被默默丢掉（`extra="ignore"`），所以新固件加字段不会搞坏旧
SDK。

---

## `ExpansionDevice`

```python
ExpansionDevice(address=0x68)
```

* `address` 是 7 位 I2C 地址（`0..0x7F`）。
* 板载 INA219 会被固件从扩展扫描结果中过滤掉，`exp` 只表示开发者外接模块。
* 固件发出的是 `{"addr": 104}`；这个模型也接受 `"address"` 作为同义
  词。内部都会归一化到 `address`。

---

## `ChargeState`

```python
class ChargeState(str, Enum):
    IDLE     = "idle"
    DETECTED = "detected"
    CHARGING = "charging"
    FULL     = "full"
    FAULT    = "fault"
```

字符串值跟固件发的完全一致，所以 `StateSnapshot.charge.value` 和
`charge.name` 都能用。

---

## 异常

所有 SDK 异常都继承自 `DeskCarError`。

| 异常 | 触发场景 |
| :--- | :--- |
| `DeskCarError`       | 基础异常 |
| `TransportError`     | WS / HTTP 失败（建立、发送、接收） |
| `ProtocolError`      | 车端发来 SDK 解析不了的东西 |
| `NotConnectedError`  | 还没 `connect()` 或者已经 `close()` 之后又调方法 |
| `DeskCarTimeoutError` | 发现阶段超时，没人应答 |

```python
from deskcar.exceptions import DeskCarError

try:
    car = await Chassis.discover_first(timeout=2.0)
except DeskCarTimeoutError:
    ...   # 局域网上没车
```

---

## Transport

SDK 的 `Transport` 是单条 `websockets` 连接加一个标准库 HTTP GET 的薄
封装。多数用户不会直接碰它，但公开方法列一下：

| 方法 | 备注 |
| :--- | :--- |
| `await transport.open()` / `close()` | 生命周期 |
| `await transport.send(payload: dict)` | 发一条 JSON WS 帧 |
| `await transport.http_get(path: str) -> bytes` | 一次 HTTP GET |
| `async for ev in transport.events(): ...` | 原始事件 payload |
| `transport.info` | 绑定的 `ChassisInfo` |

要换别的 transport（比如 USB-CDC 或者测试用的 mock），继承
`deskcar.transport.Transport` 然后赋给 `Chassis._transport` 即可。
