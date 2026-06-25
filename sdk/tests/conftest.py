"""Shared fixtures for the DeskCar SDK test suite.

The transport is mocked end-to-end so tests can run on any host with no
real DeskCar reachable. The mock records every command the SDK sends and
replays a programmable stream of state frames.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from deskcar.chassis import Chassis
from deskcar.transport import Transport
from deskcar.types import ChassisInfo


class _FakeWebSocket:
    """Just enough of websockets.ClientConnection to drive the SDK."""

    def __init__(self, inbox: asyncio.Queue, outbox: list[bytes]) -> None:
        self._inbox = inbox
        self._outbox = outbox

    async def send(self, data: str) -> None:
        self._outbox.append(data.encode("utf-8"))

    async def recv(self) -> str:
        item = await self._inbox.get()
        # Real websockets return str for text frames, bytes for binary.
        if isinstance(item, (bytes, bytearray)):
            return item.decode("utf-8")
        return item

    async def close(self) -> None:
        return None


class FakeTransport(Transport):
    """In-memory Transport: every send/recv is observable in tests."""

    def __init__(self, info: ChassisInfo) -> None:
        super().__init__(info, open_timeout=0.1)
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.sent: list[bytes] = []

    async def open(self) -> None:  # type: ignore[override]
        self._ws = _FakeWebSocket(self.inbox, self.sent)  # type: ignore[assignment]
        self._start_reader()

    def feed(self, payload: dict[str, Any] | bytes) -> None:
        if isinstance(payload, dict):
            payload = json.dumps(payload).encode("utf-8")
        self.inbox.put_nowait(payload)

    async def http_get(self, path: str) -> bytes:  # type: ignore[override]
        if path == "/api/v1/state":
            return (b'{"type":"state","ts":1,"v":3.95,"i":-100,"soc":80,'
                    b'"charge":"charging","wifi":"AP","ip":"192.168.4.1",'
                    b'"ap_ip":"192.168.4.1","sta_ip":"","ssid":"",'
                    b'"sta_configured":false,"speed":200,"exp":[]}')
        if path == "/api/v1/devices":
            return b'{"devices":[{"addr":64},{"addr":104}]}'
        if path == "/api/v1/wifi":
            return (b'{"wifi":"AP+STA","ip":"192.168.1.42",'
                    b'"ap_ip":"192.168.4.1","sta_ip":"192.168.1.42",'
                    b'"ssid":"LabWiFi","sta_configured":true}')
        return b"{}"

    async def http_post_json(self, path: str, payload: dict[str, Any]) -> bytes:  # type: ignore[override]
        if path == "/api/v1/wifi" and payload.get("ssid"):
            return b'{"ok":true,"restart_required":true}'
        return b'{"ok":false}'

    async def http_delete(self, path: str) -> bytes:  # type: ignore[override]
        if path == "/api/v1/wifi":
            return b'{"ok":true,"restart_required":true}'
        return b'{"ok":false}'


@pytest.fixture
def chassis() -> Chassis:
    """A Chassis whose transport is a FakeTransport, ready to drive."""
    car = Chassis.from_host("192.168.4.1")
    car._transport = FakeTransport(car.info)  # intentional test-only swap
    return car
