"""Pydantic models for the DeskCar wire protocol.

These types are the public contract between the firmware and any client
(Python SDK, custom integrations, test harnesses). See
``docs/PROTOCOL.md`` for the canonical schema.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import model_validator


class ChargeState(str, Enum):
    IDLE = "idle"
    DETECTED = "detected"
    CHARGING = "charging"
    FULL = "full"
    FAULT = "fault"


class ExpansionDevice(BaseModel):
    model_config = ConfigDict(frozen=True)

    address: int = Field(ge=0, le=0x7F, description="7-bit I2C address")

    @model_validator(mode="before")
    @classmethod
    def _accept_addr_alias(cls, data: Any) -> Any:
        """Firmware emits ``{"addr": 0x40}`` (C-side field name); let that
        be spelled ``address`` on the Python side without breaking parsing."""
        if isinstance(data, dict) and "address" not in data and "addr" in data:
            return {**data, "address": data["addr"]}
        return data


class StateSnapshot(BaseModel):
    """Single telemetry frame broadcast by the car over WebSocket."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["state"] = "state"
    ts: int = Field(description="Milliseconds since boot")
    v: float | None = Field(default=None, description="Battery voltage (V)")
    i: float | None = Field(default=None, description="Battery current (mA)")
    soc: float | None = Field(default=None, ge=0, le=100, description="State of charge (%)")
    charge: ChargeState = ChargeState.IDLE
    wifi: str | None = None
    speed: int | None = Field(default=None, ge=0, le=255, description="Global PWM cap")
    exp: list[ExpansionDevice] = Field(default_factory=list)


class ChassisInfo(BaseModel):
    """Result of LAN discovery."""

    model_config = ConfigDict(frozen=True)

    host: str
    port: int = 80
    name: str | None = None
    mac: str | None = None
    firmware_version: int | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}/api/v1/stream"


class DriveCommand(BaseModel):
    """Reactive PWM command. Range -255..255 per wheel."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["drive"] = "drive"
    left: int = Field(ge=-255, le=255)
    right: int = Field(ge=-255, le=255)


class StopCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["stop"] = "stop"


class SetSpeedCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["set_speed"] = "set_speed"
    value: int = Field(ge=0, le=255)


class ScanExpansionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["scan_expansion"] = "scan_expansion"


class ResetCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["reset"] = "reset"


Command = DriveCommand | StopCommand | SetSpeedCommand | ScanExpansionCommand | ResetCommand
