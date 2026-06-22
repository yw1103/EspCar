"""Smoke tests: assert the SDK can decode the EXACT JSON the firmware emits.

The shapes here are taken from ``firmware/src/server.cpp`` -- if you
change the firmware wire format you must change this test, not the
``StateSnapshot`` model.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from deskcar.types import ChargeState, ExpansionDevice, StateSnapshot

# ---- WS /api/v1/stream state broadcast ----------------------------
# Copied verbatim from server.cpp::broadcast_state()
WS_STATE_FULL = {
    "type": "state",
    "ts": 12345,
    "v": 3.95,
    "i": -100.5,
    "soc": 72,
    "charge": "charging",
    "exp": [{"addr": 64}, {"addr": 104}],
    "wifi": "AP+STA",
    "speed": 200,
}


# ---- HTTP GET /api/v1/state (after fix: matches the WS shape) -----
HTTP_STATE_FULL = {
    "type": "state",
    "ts": 67890,
    "v": 3.91,
    "i": -120.0,
    "soc": 80,
    "charge": "charging",
    "exp": [],
    "wifi": "AP",
    "speed": 200,
}


def test_ws_state_decodes_into_snapshot() -> None:
    snap = StateSnapshot.model_validate(WS_STATE_FULL)
    assert snap.ts == 12345
    assert snap.v == 3.95
    assert snap.i == -100.5
    assert snap.soc == 72
    assert snap.charge is ChargeState.CHARGING
    assert snap.wifi == "AP+STA"
    assert snap.speed == 200
    assert [d.address for d in snap.exp] == [0x40, 0x68]


def test_http_state_decodes_into_snapshot() -> None:
    snap = StateSnapshot.model_validate(HTTP_STATE_FULL)
    assert snap.ts == 67890
    assert snap.v == 3.91
    assert snap.soc == 80
    assert snap.charge is ChargeState.CHARGING
    assert snap.exp == []


def test_ws_state_ignores_unknown_extra_fields() -> None:
    payload = dict(WS_STATE_FULL, future_field="ignore-me", fw_build="abc123")
    snap = StateSnapshot.model_validate(payload)
    assert snap.ts == 12345


def test_ws_state_rejects_missing_required_ts() -> None:
    bad = dict(WS_STATE_FULL)
    bad.pop("ts")
    with pytest.raises(ValidationError):
        StateSnapshot.model_validate(bad)


# ---- /api/v1/devices shape ----------------------------------------
def test_devices_list_decodes_into_expansion_devices() -> None:
    payload = {"devices": [{"addr": 0x40}, {"addr": 0x68}, {"addr": 0x3C}]}
    devices = [ExpansionDevice(address=int(d["addr"])) for d in payload["devices"]]
    assert [d.address for d in devices] == [0x40, 0x68, 0x3C]