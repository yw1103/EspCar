"""End-to-end tests for Chassis using the FakeTransport fixture."""
from __future__ import annotations

import asyncio
import json

import pytest

from deskcar import Chassis, ExpansionDevice, StateSnapshot, WifiSnapshot
from deskcar.types import ChargeState


def _sent_payloads(chassis: Chassis) -> list[dict[str, object]]:
    """Decode every WebSocket frame the SDK sent as a JSON object."""
    return [json.loads(frame.decode("utf-8")) for frame in chassis._transport.sent]


async def test_drive_sends_correct_wire_payload(chassis: Chassis) -> None:
    await chassis.connect()
    await chassis.drive(left=120, right=-80)
    assert _sent_payloads(chassis) == [{"type": "drive", "left": 120, "right": -80}]
    await chassis.close()


async def test_stop_emits_stop_command(chassis: Chassis) -> None:
    await chassis.connect()
    await chassis.stop()
    assert _sent_payloads(chassis) == [{"type": "stop"}]
    await chassis.close()


async def test_set_speed_cap_bounds(chassis: Chassis) -> None:
    await chassis.connect()
    await chassis.set_speed_cap(180)
    assert _sent_payloads(chassis) == [{"type": "set_speed", "value": 180}]
    await chassis.close()


async def test_scan_expansion_returns_typed_devices(chassis: Chassis) -> None:
    await chassis.connect()
    devices = await chassis.scan_expansion()
    assert devices == [ExpansionDevice(address=0x68), ExpansionDevice(address=0x3C)]
    sent = _sent_payloads(chassis)
    assert sent == [{"type": "scan_expansion"}]
    await chassis.close()


async def test_read_state_parses_snapshot(chassis: Chassis) -> None:
    await chassis.connect()
    snap = await chassis.read_state()
    assert isinstance(snap, StateSnapshot)
    assert snap.charge is ChargeState.CHARGING
    assert snap.soc == 80
    assert snap.ip == "192.168.4.1"
    await chassis.close()


async def test_read_wifi_parses_snapshot(chassis: Chassis) -> None:
    await chassis.connect()
    wifi = await chassis.read_wifi()
    assert isinstance(wifi, WifiSnapshot)
    assert wifi.wifi == "AP+STA"
    assert wifi.ip == "192.168.1.42"
    assert wifi.ssid == "LabWiFi"
    assert wifi.sta_configured is True
    await chassis.close()


async def test_configure_wifi_returns_ok(chassis: Chassis) -> None:
    await chassis.connect()
    assert await chassis.configure_wifi("LabWiFi", "secret") is True
    await chassis.close()


async def test_clear_wifi_returns_ok(chassis: Chassis) -> None:
    await chassis.connect()
    assert await chassis.clear_wifi() is True
    await chassis.close()


async def test_events_yields_snapshot_then_raw(chassis: Chassis) -> None:
    await chassis.connect()
    chassis.feed({"type": "state", "ts": 1, "v": 3.9, "i": 0, "soc": 50, "charge": "idle"})
    chassis.feed({"type": "device_attached", "address": 64})

    received: list[object] = []

    async def first_two() -> None:
        async for ev in chassis.events():
            received.append(ev)
            if len(received) == 2:
                return

    await asyncio.wait_for(first_two(), timeout=1.0)
    assert isinstance(received[0], StateSnapshot)
    assert received[0].charge is ChargeState.IDLE
    assert received[1] == {"type": "device_attached", "address": 64}
    await chassis.close()


async def test_connect_auto_drains_background_frames(chassis: Chassis) -> None:
    await chassis.connect()
    try:
        chassis.feed(
            {"type": "state", "ts": 1, "v": 3.9, "i": 0, "soc": 50, "charge": "idle"}
        )
        chassis.feed(
            {"type": "state", "ts": 2, "v": 3.8, "i": 0, "soc": 49, "charge": "idle"}
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert chassis._transport.inbox.empty()
    finally:
        await chassis.close()


async def test_start_event_drain_is_backwards_compatible_noop(chassis: Chassis) -> None:
    await chassis.connect()
    drain = chassis.start_event_drain()
    try:
        await asyncio.sleep(0)
        assert not drain.done()
    finally:
        drain.cancel()
        with pytest.raises(asyncio.CancelledError):
            await drain
        await chassis.close()


async def test_async_context_manager(chassis: Chassis) -> None:
    async with chassis as car:
        await car.drive(50, 50)
        assert car._transport.sent
    assert chassis._transport._ws is None


async def test_drive_before_connect_raises(chassis: Chassis) -> None:
    from deskcar.exceptions import NotConnectedError

    with pytest.raises(NotConnectedError):
        await chassis.drive(0, 0)
