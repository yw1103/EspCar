"""LAN discovery for DeskCar chassis.

Sends a UDP broadcast on :data:`DISCOVERY_PORT`; each car responds with a
JSON advertisement that the SDK turns into a :class:`ChassisInfo`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import suppress

from deskcar.exceptions import DeskCarTimeoutError
from deskcar.types import ChassisInfo

_LOG = logging.getLogger(__name__)

DISCOVERY_PORT = 30303
DISCOVERY_MAGIC = b"DESKCAR_DISCOVER_V1\r\n"
DISCOVERY_ADDRESS = "255.255.255.255"


async def _advertisement_stream(
    timeout: float, interface_ip: str | None = None
) -> AsyncIterator[ChassisInfo]:
    """Yield ``ChassisInfo`` for every chassis heard on the wire."""
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: asyncio.DatagramProtocol(),
        local_addr=("0.0.0.0", 0),
        allow_broadcast=True,
    )
    try:
        sock = transport.get_extra_info("socket")
        if sock is not None and interface_ip:
            with suppress(OSError):
                sock.setsockopt(
                    __import__("socket").IPPROTO_IP,
                    __import__("socket").IP_MULTICAST_IF,
                    __import__("socket").inet_aton(interface_ip),
                )

        # Spawn a small reader coroutine that funnels datagrams into a queue.
        queue: asyncio.Queue[bytes] = asyncio.Queue()

        class _Reader(asyncio.DatagramProtocol):
            def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
                queue.put_nowait(data)

            def connection_made(self, transport_obj: object) -> None:  # pragma: no cover
                pass

            def error_received(self, exc: Exception) -> None:  # pragma: no cover
                _LOG.debug("discovery socket error: %s", exc)

        transport.close()
        transport, _ = await loop.create_datagram_endpoint(
            _Reader, local_addr=("0.0.0.0", 0), allow_broadcast=True
        )
        transport.sendto(DISCOVERY_MAGIC, (DISCOVERY_ADDRESS, DISCOVERY_PORT))

        deadline = loop.time() + timeout
        seen: set[str] = set()
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                return
            try:
                data = await asyncio.wait_for(queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                return
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                _LOG.debug("ignoring malformed advertisement: %r", data)
                continue
            try:
                info = ChassisInfo(
                    host=payload["host"],
                    port=int(payload.get("port", 80)),
                    name=payload.get("name"),
                    mac=payload.get("mac"),
                    firmware_version=payload.get("v"),
                )
            except (KeyError, ValueError) as exc:
                _LOG.debug("ignoring incomplete advertisement: %s", exc)
                continue
            if info.host in seen:
                continue
            seen.add(info.host)
            yield info
    finally:
        transport.close()


async def discover(timeout: float = 2.0) -> list[ChassisInfo]:
    """Return every chassis heard within ``timeout`` seconds."""
    return [info async for info in _advertisement_stream(timeout)]


async def discover_first(timeout: float = 2.0) -> ChassisInfo:
    """Return the first chassis heard, or raise :class:`DeskCarTimeoutError`."""
    async for info in _advertisement_stream(timeout):
        return info
    raise DeskCarTimeoutError(f"no DeskCar chassis found within {timeout}s")
