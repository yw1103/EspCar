# deskcar SDK Reference

Complete reference for every public symbol in `deskcar`.
Generated against `sdk/src/deskcar/__init__.py` and
`sdk/tests/test_wire_shape.py` (which is the ground truth for what the
firmware actually emits).

## Top-level

```python
from deskcar import (
    Chassis,            # high-level client
    ChassisInfo,        # discovery result
    StateSnapshot,      # parsed state frame
    ExpansionDevice,    # one I2C device on the magnetic port
    ChargeState,        # enum: idle / detected / charging / full / fault
    DeskCarError,       # base exception
    DeskCarTimeoutError,
    NotConnectedError,
    ProtocolError,
    TransportError,
)
```

---

## `Chassis`

Async, typed high-level client.  Use as a context manager or call
`connect()` / `close()` explicitly.

```python
async with await Chassis.discover_first() as car:
    await car.drive(120, 120)
```

### Constructors

#### `Chassis.discover(timeout=2.0) -> list[Chassis]`

Broadcasts a UDP discovery packet and returns one `Chassis` per car
heard before the deadline.

#### `Chassis.discover_first(timeout=2.0) -> Chassis`

Same, but returns the first car heard.  Raises `DeskCarTimeoutError`
on timeout.

#### `Chassis.from_host(host: str, *, port: int = 80) -> Chassis`

Skip discovery and talk to a known IP.  Useful in CI / on a wired
desk.

### Lifecycle

| Method | Notes |
| :--- | :--- |
| `await car.connect()` | opens the WS + HTTP sessions |
| `await car.close()` | tears them down; safe to call twice |
| `async with await Chassis.discover_first() as car: ...` | shorthand |
| `car.info` | the `ChassisInfo` this instance is bound to |

### Reactive control

| Method | Effect | Wire command |
| :--- | :--- | :--- |
| `await car.drive(left: int, right: int)` | per-wheel PWM -255..255 | `{"type":"drive","left":..,"right":..}` |
| `await car.stop()` | hard stop (uses `ledcWrite(0)`) | `{"type":"stop"}` |
| `await car.set_speed_cap(value: int)` | global PWM cap 0..255 | `{"type":"set_speed","value":..}` |

`drive` does **not** block; it is one WS frame.  If you need to keep
the motors on, send a `drive` at least every 200 ms — that is the
firmware’s `loop()` cadence for state broadcasts, after which a
`stop` is implicitly applied if the WS is lost.

### Introspection

| Method | Effect |
| :--- | :--- |
| `await car.scan_expansion() -> list[ExpansionDevice]` | forces a fresh I2C scan, returns the device list |
| `await car.read_state() -> StateSnapshot` | one-shot telemetry frame via HTTP |
| `car.feed(payload)` | test hook: inject a wire frame into the inbound queue |

### Event stream

```python
async for ev in car.events():
    if isinstance(ev, StateSnapshot):
        ...   # typed access
    else:
        ...   # raw dict: device_attached, error, encoder, ...
```

`events()` is an async iterator that yields forever.  Cancel-safe: if
the WS drops, the iterator returns and the next `connect()` opens a
fresh stream.

The SDK does **not** block on partial frames; the underlying transport
reassembles WS messages for you.

---

## `ChassisInfo`

Frozen pydantic model returned by discovery.

```python
info = ChassisInfo(host="192.168.4.1", port=80, name="deskcar-7c9e")
info.base_url   # "http://192.168.4.1:80"
info.ws_url     # "ws://192.168.4.1:80/api/v1/stream"
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `host` | str | IP address |
| `port` | int | TCP port (default 80) |
| `name` | str \| None | human-readable label from the advertisement |
| `mac` | str \| None | car MAC (if advertised) |
| `firmware_version` | int \| None | protocol version, see `firmware/include/protocol.h` |

---

## `StateSnapshot`

The shape that comes back from `read_state()` and from every WS
`state` event.  All fields except `type`, `ts`, `charge` are optional,
so a snapshot from a brand-new car (no INA219 yet) still parses.

```python
class StateSnapshot(BaseModel):
    type: Literal["state"] = "state"
    ts: int                              # ms since boot
    v: float | None = None               # V
    i: float | None = None               # mA
    soc: float | None = None             # %
    charge: ChargeState = ChargeState.IDLE
    wifi: str | None = None              # "AP" / "STA" / "AP+STA"
    speed: int | None = None             # 0..255
    exp: list[ExpansionDevice] = []      # I2C devices
```

Unknown fields are silently ignored (`extra="ignore"`), so a newer
firmware can add fields without breaking an older SDK.

---

## `ExpansionDevice`

```python
ExpansionDevice(address=0x40)
```

* `address` is a 7-bit I2C address (`0..0x7F`).
* The firmware emits `{"addr": 64}`; the model also accepts
  `"address"` as a synonym.  Internally, both end up as `address`.

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

String values match exactly what the firmware sends, so
`StateSnapshot.charge.value` and `charge.name` are both useful.

---

## Exceptions

All SDK exceptions inherit from `DeskCarError`.

| Exception | When |
| :--- | :--- |
| `DeskCarError` | base |
| `TransportError` | WS / HTTP failure (open, send, recv) |
| `ProtocolError` | the car sent something the SDK could not parse |
| `NotConnectedError` | you called a method before `connect()` or after `close()` |
| `DeskCarTimeoutError` | discovery timed out before a car answered |

```python
from deskcar.exceptions import DeskCarError

try:
    car = await Chassis.discover_first(timeout=2.0)
except DeskCarTimeoutError:
    ...   # nothing on the LAN
```

---

## Transport

The SDK’s `Transport` is a thin async wrapper around a single
`websockets` connection plus a stdlib HTTP GET.  Most users never touch
it directly, but the public methods are:

| Method | Notes |
| :--- | :--- |
| `await transport.open()` / `close()` | lifecycle |
| `await transport.send(payload: dict)` | one JSON WS frame |
| `await transport.http_get(path: str) -> bytes` | one HTTP GET |
| `async for ev in transport.events(): ...` | raw event payloads |
| `transport.info` | the bound `ChassisInfo` |

To swap in a different transport (e.g. USB-CDC, mock for tests),
subclass `deskcar.transport.Transport` and assign it to
`Chassis._transport`.