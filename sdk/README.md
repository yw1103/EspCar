# deskcar — Python SDK for the DeskCar chassis

Async, typed, zero-CV-dependency Python client for the DeskCar ESP32
desktop smart chassis.  Speaks the same JSON-over-WebSocket protocol
that ``firmware/src/server.cpp`` implements; see
``docs/PROTOCOL.md`` for the full wire contract.

## Install

```bash
pip install deskcar
# or, editable from this repo:
pip install -e ./sdk[dev]
```

## Quickstart

```python
import asyncio
from deskcar import Chassis, StateSnapshot

async def main() -> None:
    car = await Chassis.discover_first()       # UDP LAN scan
    await car.connect()                        # opens WS + HTTP

    # Reactive control: signed PWM per wheel, range [-255, 255].
    await car.drive(left=120, right=120)
    await asyncio.sleep(1.0)
    await car.stop()

    # Read the latest telemetry snapshot.
    snap: StateSnapshot = await car.read_state()
    print(snap.charge.name, snap.v, snap.soc)

    # List devices on the magnetic expansion port.
    devices = await car.scan_expansion()       # forces an I2C scan
    print([d.address for d in devices])

    # Stream state frames at ~5 Hz until cancelled.
    async for ev in car.events():
        if isinstance(ev, StateSnapshot):
            print("ts", ev.ts, "v", ev.v)

asyncio.run(main())
```

## What the SDK gives you

| Method                           | What it does                                         |
| :------------------------------- | :--------------------------------------------------- |
| `Chassis.discover(timeout)`      | UDP-scan the LAN, returns every car heard.           |
| `Chassis.discover_first(timeout)`| First car heard, or `DeskCarTimeoutError`.           |
| `Chassis.from_host("1.2.3.4")`   | Skip discovery when you already know the IP.         |
| `Chassis.connect()` / `close()`  | Open / tear down WS + HTTP.                          |
| `Chassis.drive(left, right)`     | Per-wheel PWM, -255..255.                            |
| `Chassis.stop()`                 | Hard stop.                                           |
| `Chassis.set_speed_cap(value)`   | Global PWM cap 0..255 (persisted by the firmware).   |
| `Chassis.scan_expansion()`       | Returns the I2C devices on the magnetic port.        |
| `Chassis.read_state()`           | One-shot telemetry snapshot.                         |
| `Chassis.events()`               | Async iterator over WS frames (state + extension).   |

The SDK itself does **not** plan paths, dock, or otherwise close a
control loop — those live in the PC-side ``orchestrator/`` package,
which subscribes to the same event stream and issues reactive
``drive`` / ``stop`` commands.

## Development

```bash
pip install -e ./sdk[dev]
pytest
ruff check src/deskcar tests
mypy src/deskcar --no-incremental
```

## License

MIT