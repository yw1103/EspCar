# DeskCar v2 线协议

DeskCar 固件（`firmware/src/server.cpp`）和 Python SDK（`sdk/src/deskcar/`）在
WebSocket + HTTP 上说同一套 JSON 协议。本文档就是这份契约的权威定义——你改
哪一边都必须改另一边，`sdk/tests/test_wire_shape.py` 这条冒烟测试会一直盯
着它们一致。

## 传输层

| 通道 | 端点 | 方向 | 备注 |
| :--- | :--- | :--- | :--- |
| WebSocket | `ws://<host>:80/api/v1/stream` | 双向 | 命令 + 事件流 |
| HTTP GET   | `http://<host>:80/api/v1/state` | PC <- 车 | 最新一次状态快照 |
| HTTP GET   | `http://<host>:80/api/v1/devices` | PC <- 车 | 扩展口 I2C 扫描结果 |
| HTTP POST  | `http://<host>:80/api/v1/move` | PC -> 车 | 一次性下发驱动指令 |
| HTTP GET   | `http://<host>:80/`、`/control`、`/speed`、`/data` | PC -> 车 | v1 手机 H5 兼容接口 |

默认端口：**80**。默认连的是小车开放热点 `ESP32_Car_Control`
（`192.168.4.1`）。

## WebSocket 命令（PC -> 车）

所有命令都是 JSON 对象，必须带 `"type"` 字段作为判别。

### `drive` — 每个轮子的 PWM

```json
{ "type": "drive", "left": -255, "right": 255 }
```

* `left`、`right` 是带符号整数，范围 `[-255, 255]`。
* 固件会先套上全局 `speed` 上限，再用 50~100 ms 的 PWM 缓启斜坡（v1 关键
  修复，避免 brownout 重启），最后驱动 DRV8833。
* 发 `0, 0` **不是**硬刹车；要用 `stop` 命令（它强制对所有通道
  `ledcWrite(0)`，这是 ESP32 上唯一能释放 LEDC 引脚的办法）。

### `set_speed` — 全局 PWM 上限

```json
{ "type": "set_speed", "value": 200 }
```

`value` 会被夹紧到 `[0, 255]`。影响之后所有 `drive` 命令；这个值也会回
映到 `state` 事件的 `"speed"` 字段。

### `stop` — 硬刹车

```json
{ "type": "stop" }
```

把所有电机通道强制拉到 0% 占空比。断开连接以及任何安全事件时都要调它。

### `scan_expansion` — 强制扫一次 I2C

```json
{ "type": "scan_expansion" }
```

让固件立刻对磁吸扩展口做一次 I2C 扫描。结果会在下一次 `state` 事件的
`exp` 字段里，同时也通过 `GET /api/v1/devices` 暴露。

### `reset` — 重启 MCU

```json
{ "type": "reset" }
```

执行 `ESP.restart()`。仅在开发 / OTA 场景用。

## WebSocket 事件（车 -> PC）

### `state` — 遥测快照，约 5 Hz 广播

```json
{
  "type": "state",
  "ts": 12345,
  "v": 3.95,
  "i": -120.5,
  "soc": 80,
  "charge": "charging",
  "exp": [{"addr": 64}, {"addr": 104}],
  "wifi": "AP+STA",
  "speed": 200
}
```

| 字段 | 类型 | 含义 |
| :--- | :--- | :--- |
| `type`   | `"state"` | 判别符 |
| `ts`     | int       | 距上电的毫秒数（和 MCU 的 `millis()` 一致） |
| `v`      | float     | 电池电压，V（INA219 测得） |
| `i`      | float     | 电池电流，mA（充电时为负） |
| `soc`    | int       | 剩余电量百分比 |
| `charge` | string    | `idle` / `detected` / `charging` / `full` / `fault` 之一 |
| `exp`    | array     | 当前已挂载的扩展口设备 |
| `wifi`   | string    | `"AP"` / `"STA"` / `"AP+STA"` |
| `speed`  | int       | 当前全局 PWM 上限 |

`exp` 里每条都是 `{"addr": <7 位 I2C 地址>}`——SDK 解析时既接受
`addr`（固件命名）也接受 `address`（Python 命名）。

### `encoder` — 轮子编码器计数

```json
{ "type": "encoder", "left": 1234, "right": 1230, "dt": 200 }
```

* `left`、`right` 是带符号的脉冲计数（7-PPR 霍尔传感器 ×4 倍频 = 28 cpr）。
* `dt` 是两帧之间的间隔，毫秒。

### `device_attached` / `device_detached`

```json
{ "type": "device_attached", "address": 64 }
{ "type": "device_detached", "address": 64 }
```

扩展口 INT 引脚电平变化时触发。和 `scan_expansion` 配合就能维护一份
实时的设备清单。

### `error`

```json
{ "type": "error", "msg": "i2c: bus stuck" }
```

自由格式的错误字符串。SDK 直接把它当原始 dict 抛出来，业务代码自己分支
处理。

## HTTP

### `GET /api/v1/state`

和 `state` 事件一样的结构。是 SDK 的 `Chassis.read_state()` 取一次性快
照的接口。

### `GET /api/v1/devices`

```json
{ "devices": [ {"addr": 64}, {"addr": 104} ] }
```

### `POST /api/v1/move`

```json
{ "left": 100, "right": 100 }
```

返回：`{"ok": true}`。功能和 WS 上的 `drive` 一样，但用 `curl` 之类的
一次性脚本调用更顺手。

## v1 兼容（保留给手机 H5 控制器）

| 路由 | 方法 | 作用 |
| :--- | :--- | :--- |
| `/` | GET | 返回 v1 H5 页面（index_html.h） |
| `/control?dir=F\|B\|L\|R\|S` | GET | v1 风格的驱动 / 停止 |
| `/speed?val=0..255` | GET | 等价于 `set_speed` |
| `/data` | GET | `{"left": <count>, "right": <count>}` 编码器快照 |

这些接口留着，是为了烧 v2 固件之后原来的 v1 手机控制器还能用。新写的代
码请走 `/api/v1/*` 命名空间和 WebSocket 流。

## 发现（Discovery）

PC 端往 `255.255.255.255:30303` 广播 `DESKCAR_DISCOVER_V1\r\n`；每台车
回一份 JSON 宣告：

```json
{ "host": "192.168.4.1", "port": 80, "name": "deskcar-7c9e", "v": 1 }
```

`v` 是固件协议版本（见 `firmware/include/protocol.h`）。SDK 的
`Chassis.discover()` / `discover_first()` 就是基于这个协议做的。
