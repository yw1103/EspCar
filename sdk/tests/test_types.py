"""Unit tests for the wire-protocol pydantic models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from deskcar.types import (
    ChargeState,
    ChassisInfo,
    DriveCommand,
    ExpansionDevice,
    ScanExpansionCommand,
    SetSpeedCommand,
    StateSnapshot,
    StopCommand,
)


def test_charge_state_values() -> None:
    assert ChargeState.CHARGING.value == "charging"
    assert ChargeState.IDLE.value == "idle"
    assert ChargeState("full") is ChargeState.FULL


def test_state_snapshot_parses_real_wire_payload() -> None:
    raw = {
        "type": "state",
        "ts": 12_345,
        "v": 3.91,
        "i": -120.5,
        "soc": 72,
        "charge": "charging",
        "wifi": "AP+STA",
        "speed": 200,
        "exp": [{"address": 104}, {"address": 60}],
    }
    snap = StateSnapshot.model_validate(raw)
    assert snap.ts == 12_345
    assert snap.v == 3.91
    assert snap.i == -120.5
    assert snap.soc == 72
    assert snap.charge is ChargeState.CHARGING
    assert snap.wifi == "AP+STA"
    assert snap.speed == 200
    assert [d.address for d in snap.exp] == [0x68, 0x3C]


def test_state_snapshot_rejects_bogus_charge() -> None:
    with pytest.raises(ValidationError):
        StateSnapshot.model_validate({"type": "state", "ts": 0, "charge": "BOGUS"})


def test_state_snapshot_ignores_unknown_fields() -> None:
    snap = StateSnapshot.model_validate({"type": "state", "ts": 0, "future_field": 42})
    assert snap.ts == 0


def test_drive_command_bounds() -> None:
    DriveCommand(left=-255, right=255)
    with pytest.raises(ValidationError):
        DriveCommand(left=-256, right=0)
    with pytest.raises(ValidationError):
        DriveCommand(left=0, right=256)


def test_drive_command_serialization() -> None:
    cmd = DriveCommand(left=-100, right=100)
    assert cmd.model_dump() == {"type": "drive", "left": -100, "right": 100}
    assert StopCommand().model_dump() == {"type": "stop"}
    assert SetSpeedCommand(value=150).model_dump() == {"type": "set_speed", "value": 150}
    assert ScanExpansionCommand().model_dump() == {"type": "scan_expansion"}


def test_chassis_info_urls() -> None:
    info = ChassisInfo(host="192.168.4.1")
    assert info.base_url == "http://192.168.4.1:80"
    assert info.ws_url == "ws://192.168.4.1:80/api/v1/stream"


def test_expansion_device_frozen() -> None:
    dev = ExpansionDevice(address=0x68)
    with pytest.raises(ValidationError):
        ExpansionDevice(address=128)  # 7-bit address bound
    with pytest.raises((ValidationError, Exception)):
        # frozen model rejects mutation
        dev.address = 0x50  # type: ignore[misc]
