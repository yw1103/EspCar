# DeskCar

ESP32 two-wheel desktop smart chassis. v1 was a Wi-Fi controlled toy; v2
adds a USB-camera vision loop, Qi wireless charging, a 5-pin magnetic
expansion port, and a typed Python SDK for the host PC.

## What's in the box

| Path                | Role                                                 |
| :------------------ | :--------------------------------------------------- |
| `firmware/`         | ESP32 Arduino / PlatformIO firmware (compiles)       |
| `sdk/`              | `deskcar` Python SDK (async, typed, pip-installable) |
| `orchestrator/`     | PC-side vision + auto-dock + obstacle avoidance      |
| `hardware/`         | KiCad schematics, PCB, BOM, mechanical drawings      |
| `docs/`             | Protocol, SDK reference, calibration, hardware notes |
| `examples/`         | Runnable demos                                       |

## Quick start

```bash
# 1. install the SDK
pip install -e ./sdk

# 2. flash the firmware (one-shot)
pio run -d firmware -t upload

# 3. drive the car from Python
python examples/read_state_demo.py
```

The car creates an open AP `ESP32_Car_Control` on first boot. Connect
your laptop to that SSID, then run the examples (default host
`192.168.4.1`).

## Key decisions (locked)

- vision runs on the host PC over a USB camera
- charging is Qi 5W inductive (1S Li-ion 1000 mAh on the car)
- expansion port is 5-pin pogo (3.3V / GND / SDA / SCL / INT) + 4 x N52 magnets
- localization: car-top ArUco + dock AprilTag (dual source)
- SDK: Python-first, typed, public protocol documented in `docs/PROTOCOL.md`

Full plan and trade-offs in [PROJECT_PLAN.md](PROJECT_PLAN.md).
## Auto-dock

To make the car self-dock, see [orchestrator/README.md](orchestrator/README.md)
and the [hardware](docs/HARDWARE.md) / [calibration](docs/CALIBRATION.md) guides.

## License

MIT
