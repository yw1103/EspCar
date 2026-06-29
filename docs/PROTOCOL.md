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
| HTTP GET   | `http://<host>:80/api/v1/wifi` | PC <- 车 | 当前 Wi-Fi / IP / 配网状态 |
| HTTP POST  | `http://<host>:80/api/v1/wifi` | PC -> 车 | 写入 STA Wi-Fi 凭据 |
| HTTP DELETE | `http://<host>:80/api/v1/wifi` | PC -> 车 | 清除 STA Wi-Fi 凭据 |
| HTTP POST  | `http://<host>:80/api/v1/move` | PC -> 车 | 一次性下发驱动指令 |
| HTTP GET   | `http://<host>:80/wifi`、`/setup` | 用户 -> 车 | 浏览器配网页 |
| HTTP GET   | `http://<host>:80/`、`/control`、`/speed`、`/data` | 用户 -> 车 | v1 手机 H5 兼容接口 |

默认端口：**80**。产品网络模型是 **STA 优先 + AP 配网/兜底**：

1. 首次启动或 STA 连接失败时，小车开启开放热点 `ESP32_Car_Control`
   （`192.168.4.1`）。
2. 用户打开 `http://192.168.4.1/wifi`，或通过 `POST /api/v1/wifi` 写入
   2.4 GHz Wi-Fi 的 SSID/密码。
3. 重启后小车优先加入用户局域网，PC/SDK 通过局域网 IP 或发现协议访问它。
4. AP 仍作为救援入口保留，方便重新配网和手机 H5 调试。

## WebSocket 命令（PC -> 车）

所有命令都是 JSON 对象，必须带 `"type"` 字段作为判别。

### `drive` — 每个轮子的 PWM

```json
{ "type": "drive", "left": -255, "right": 255 }
```

* `left`、`right` 是带符号整数，范围 `[-255, 255]`。
* 固件会先套上全局 `speed` 上限，再把目标值交给 `motor_tick()` 在主循环里
  逐步推进。换句话说，`drive` 只是下发目标，真正出波形要靠主循环持续运行。
* 输出采用 50~100 ms 的 PWM 缓启斜坡（v1 关键修复，避免 brownout 重启），
  最后驱动 DRV8833。
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

请求固件在主循环里对磁吸扩展口做一次 I2C 扫描。结果会在后续 `state` 事件的
`exp` 字段里，同时也通过 `GET /api/v1/devices` 暴露。I2C 扫描不在 HTTP/WS
异步回调里执行，避免和 INA219 采样抢占同一条 `Wire` 总线。

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
  "exp": [{"addr": 104}, {"addr": 60}],
  "wifi": "AP+STA",
  "ip": "192.168.1.42",
  "ap_ip": "192.168.4.1",
  "sta_ip": "192.168.1.42",
  "ssid": "LabWiFi",
  "sta_configured": true,
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
| `ip`     | string    | SDK 当前应优先连接的 IP；STA 已连时为 STA IP，否则为 AP IP |
| `ap_ip`  | string    | 小车 AP 侧 IP，通常是 `192.168.4.1` |
| `sta_ip` | string    | 小车在用户局域网里的 IP；未连接时为空字符串 |
| `ssid`   | string    | 已保存的 STA SSID；未配网时为空字符串 |
| `sta_configured` | bool | 是否已保存 STA 凭据 |
| `speed`  | int       | 当前全局 PWM 上限 |

`exp` 里每条都是 `{"addr": <7 位 I2C 地址>}`——SDK 解析时既接受
`addr`（固件命名）也接受 `address`（Python 命名）。板载 INA219 会从这个列表
中过滤掉；这里表达的是磁吸扩展口上的开发者模块，不是整条 I2C 总线的原始扫描结果。

`charge` 的来源有两种：如果充电模块提供 `CHRG` 引脚，固件优先使用该低有效信号；
如果没有这根线，固件使用 INA219 电流方向推断，约定 `i < 0` 表示电流流入电池。
单靠 INA219 可以可靠判断“正在充电”；满电后电流接近 0 时，固件会在高电压和小电流
死区内保持 `full`，但“是否仍在充电坞上”仍应结合上层自动回充状态机判断。

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

### `GET /wifi` / `GET /setup`

返回一个极简浏览器配网页，供用户填写 2.4 GHz Wi-Fi SSID/密码。页面内部调用
`GET/POST/DELETE /api/v1/wifi`，适合首次配网和现场恢复。

### `GET /api/v1/state`

和 `state` 事件一样的结构。是 SDK 的 `Chassis.read_state()` 取一次性快
照的接口。

### `GET /api/v1/devices`

```json
{ "devices": [ {"addr": 104}, {"addr": 60} ] }
```

返回最近一次扩展口扫描缓存。固件会低频自动刷新，也可以先发 `scan_expansion`
请求下一轮主循环扫描。

### `GET /api/v1/wifi`

```json
{
  "wifi": "AP+STA",
  "ip": "192.168.1.42",
  "ap_ip": "192.168.4.1",
  "sta_ip": "192.168.1.42",
  "ssid": "LabWiFi",
  "sta_configured": true
}
```

### `POST /api/v1/wifi`

```json
{ "ssid": "LabWiFi", "pass": "password" }
```

返回：

```json
{ "ok": true, "restart_required": true }
```

固件会把凭据保存到 ESP32 NVS。调用成功后重启 ESP32；下一次启动会优先尝试
STA 入网，8 秒内失败则保留 AP 兜底。

### `DELETE /api/v1/wifi`

清除已保存的 STA 凭据。返回：

```json
{ "ok": true, "restart_required": true }
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

PC 端往 `255.255.255.255:30303` 广播 `DESKCAR_DISCOVER_V1\r\n`；每台车回
一份 JSON 宣告。STA 已连接时 `host` 是局域网 IP；否则是 AP IP：

```json
{ "host": "192.168.4.1", "port": 80, "name": "deskcar-7c9e", "v": 1 }
```

`v` 是固件协议版本（见 `firmware/include/protocol.h`）。SDK 的
`Chassis.discover()` / `discover_first()` 就是基于这个协议做的。
