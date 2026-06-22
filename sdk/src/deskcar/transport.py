"""Async transport for DeskCar: WebSocket command/event channel + HTTP for one-shots.

The transport is intentionally tiny: the WebSocket handles high-rate commands
and a fan-out of state events, while HTTP is used for configuration that
benefits from a request/response shape (state snapshots, I2C scan).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, WebSocketException

from deskcar.exceptions import (
    NotConnectedError,
    ProtocolError,
    TransportError,
)
from deskcar.types import ChassisInfo

_LOG = logging.getLogger(__name__)


class Transport:
    """One WebSocket + one HTTP session, sharing a single asyncio loop."""

    def feed(self, payload: dict[str, Any] | bytes) -> None:
        """Inject a wire frame into the inbound event queue.

        Subclasses (e.g. the test fake) override this to make inbound data
        observable; the real transport does not need an implementation.
        """
        raise NotImplementedError

    def __init__(self, info: ChassisInfo, *, open_timeout: float = 5.0) -> None:
        self._info = info
        self._ws: ClientConnection | None = None
        self._open_timeout = open_timeout
        self._event_handlers: list[Callable[[dict[str, Any]], asyncio.Future[None] | None]] = []

    @property
    def info(self) -> ChassisInfo:
        return self._info

    async def __aenter__(self) -> Transport:
        await self.open()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def open(self) -> None:
        if self._ws is not None:
            return
        try:
            self._ws = await connect(
                self._info.ws_url,
                open_timeout=self._open_timeout,
                max_size=2**20,
            )
        except (OSError, WebSocketException) as exc:
            raise TransportError(f"failed to open {self._info.ws_url}: {exc}") from exc

    async def close(self) -> None:
        if self._ws is None:
            return
        try:
            await self._ws.close()
        except Exception:
            _LOG.debug("error closing websocket", exc_info=True)
        finally:
            self._ws = None

    def _require_ws(self) -> ClientConnection:
        if self._ws is None:
            raise NotConnectedError("call connect() first")
        return self._ws

    async def send(self, payload: dict[str, Any]) -> None:
        ws = self._require_ws()
        try:
            await ws.send(json.dumps(payload))
        except ConnectionClosed as exc:
            raise TransportError(f"websocket closed: {exc}") from exc

    async def http_get(self, path: str) -> bytes:
        """Tiny HTTP GET using stdlib (avoids an aiohttp dependency)."""

        url = f"{self._info.base_url}{path}"
        # urlopen is blocking; run it in a worker thread to keep callers async.
        try:
            return await asyncio.to_thread(self._sync_http_get, url)
        except OSError as exc:
            raise TransportError(f"HTTP GET {url} failed: {exc}") from exc

    def _sync_http_get(self, url: str) -> bytes:
        from urllib import request as urlrequest

        with urlrequest.urlopen(url, timeout=self._open_timeout) as resp:
            data: bytes = resp.read()
            return data

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        """Yield raw event payloads forever; cancel-safe."""
        ws = self._require_ws()
        while True:
            try:
                raw = await ws.recv()
            except ConnectionClosed:
                return
            if isinstance(raw, (bytes, bytearray)):
                # Binary encoder stream not yet implemented; skip.
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ProtocolError(f"bad JSON from car: {raw!r}") from exc
            yield payload
