# DeskCar v2 Wire Protocol

The DeskCar firmware (`firmware/src/server.cpp`) and the Python SDK
(`sdk/src/deskcar/`) speak the same JSON protocol on top of WebSocket +
HTTP.  This document is the canonical contract — if you change one side,
you must change the other, and the `test_wire_shape.py` smoke test
inside `sdk/tests/` will keep them honest.

## Transport

| Channel | Endpoint | Direction | Notes |
| :--- | :--- | :--- | :--- |
| WebSocket | `ws://<host>:80/api/v1/stream` | duplex | command + event stream |
| HTTP GET   | `http://<host>:80/api/v1/state` | PC <- car | latest state snapshot |
| HTTP GET   | `http://<host>:80/api/v1/devices` | PC <- car | expansion I2C scan |
| HTTP POST  | `http://<host>:80/api/v1/move` | PC -> car | one-shot drive |
| HTTP GET   | `http://<host>:80/`, `/control`, `/speed`, `/data` | PC -> car | v1 phone H5, kept for compat |

Default port: **80** on the car’s open AP `ESP32_Car_Control`
(`192.168.4.1`).

## WebSocket: commands (PC -> car)

All commands are JSON objects with a required `"type"` discriminator.

### `drive` — per-wheel PWM

```json
{ "type": "drive", "left": -255, "right": 255 }
```

* `left`, `right` are signed integers in `[-255, 255]`.
* The firmware applies the global `speed` cap, then a 50–100 ms PWM
  ramp (v1 critical fix to avoid brownout resets), then drives the
  DRV8833.
* Sending `0, 0` is **not** a hard stop; use the `stop` command
  (it forces `ledcWrite(0)` on every channel, which is the only way
  to release an LEDC-attached pin on ESP32).

### `set_speed` — global PWM cap

```json
{ "type": "set_speed", "value": 200 }
```

`value` is clamped to `[0, 255]`.  Affects every subsequent `drive`
command; the value is also reported back in the `state` event
(`"speed"` field).

### `stop` — hard stop

```json
{ "type": "stop" }
```

Forces every motor channel to 0% duty.  Call this on disconnect and on
any safety event.

### `scan_expansion` — force I2C scan

```json
{ "type": "scan_expansion" }
```

Kicks the firmware to re-scan the magnetic expansion port.  The result
is included in the next `state` event under the `exp` key, and also
exposed via `GET /api/v1/devices`.

### `reset` — reboot the MCU

```json
{ "type": "reset" }
```

Issues `ESP.restart()`.  Use only in dev / OTA scenarios.

## WebSocket: events (car -> PC)

### `state` — telemetry snapshot, broadcast at ~5 Hz

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

| Field | Type | Description |
| :--- | :--- | :--- |
| `type` | `"state"` | discriminator |
| `ts` | int | ms since boot (matches `millis()` on the MCU) |
| `v` | float | battery voltage, V (INA219) |
| `i` | float | battery current, mA (negative when charging) |
| `soc` | int | state of charge, % |
| `charge` | string | one of `idle`, `detected`, `charging`, `full`, `fault` |
| `exp` | array | currently-attached expansion devices |
| `wifi` | string | `"AP"`, `"STA"`, or `"AP+STA"` |
| `speed` | int | current global PWM cap |

Each item in `exp` is `{"addr": <7-bit I2C address>}` — the SDK accepts
both `addr` (firmware) and `address` (Python style) as input.

### `encoder` — wheel counters

```json
{ "type": "encoder", "left": 1234, "right": 1230, "dt": 200 }
```

* `left`, `right` are signed pulse counts (×4 quadrature from the
  7-PPR Hall sensors, so 28 cpr).
* `dt` is the inter-frame interval in ms.

### `device_attached` / `device_detached`

```json
{ "type": "device_attached",   "address": 64 }
{ "type": "device_detached",   "address": 64 }
```

Emitted when the INT line on the expansion port toggles.  Use these
together with `scan_expansion` to keep a live device map.

### `error`

```json
{ "type": "error", "msg": "i2c: bus stuck" }
```

Free-form error string.  The SDK yields this as a raw dict; consumers
can branch on it.

## HTTP

### `GET /api/v1/state`

Same shape as the `state` event.  Used by the SDK’s
`Chassis.read_state()` to grab a one-shot snapshot.

### `GET /api/v1/devices`

```json
{ "devices": [ {"addr": 64}, {"addr": 104} ] }
```

### `POST /api/v1/move`

```json
{ "left": 100, "right": 100 }
```

Reply: `{"ok": true}`.  Functionally equivalent to a `drive` command
sent over WS, but easier to use from a `curl` session or a one-shot
script.

## v1 compatibility (kept for the phone H5 controller)

| Route | Method | Effect |
| :--- | :--- | :--- |
| `/` | GET | returns the v1 H5 page (index_html.h) |
| `/control?dir=F\|B\|L\|R\|S` | GET | v1-style drive / stop |
| `/speed?val=0..255` | GET | equivalent to `set_speed` |
| `/data` | GET | `{"left": <count>, "right": <count>}` encoder snapshot |

These exist so the existing v1 phone controller still works after the
v2 firmware flash.  New code should use the `/api/v1/*` namespace and
the WebSocket stream.

## Discovery

The PC broadcasts `DESKCAR_DISCOVER_V1\r\n` to `255.255.255.255:30303`;
each car replies with a JSON advertisement:

```json
{ "host": "192.168.4.1", "port": 80, "name": "deskcar-7c9e", "v": 1 }
```

`v` is the firmware protocol version (see `firmware/include/protocol.h`).
The SDK uses this for `Chassis.discover()` and `discover_first()`.