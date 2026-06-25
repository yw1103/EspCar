"""Async transport for DeskCar: WebSocket command/event channel + HTTP for one-shots.

The transport is intentionally tiny: the WebSocket handles high-rate commands
and a fan-out of state events, while HTTP is used for configuration that
benefits from a request/response shape (state snapshots, I2C scan).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
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
        self._reader_task: asyncio.Task[None] | None = None
        self._incoming: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=128)

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
            self._start_reader()
        except (OSError, WebSocketException) as exc:
            raise TransportError(f"failed to open {self._info.ws_url}: {exc}") from exc

    async def close(self) -> None:
        if self._ws is None:
            return
        try:
            await self._stop_reader()
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

        return await self._http_request("GET", path)

    async def http_post_json(self, path: str, payload: dict[str, Any]) -> bytes:
        return await self._http_request(
            "POST",
            path,
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )

    async def http_delete(self, path: str) -> bytes:
        return await self._http_request("DELETE", path)

    async def _http_request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
    ) -> bytes:
        url = f"{self._info.base_url}{path}"
        try:
            return await asyncio.to_thread(
                self._sync_http_request, method, url, body, content_type
            )
        except OSError as exc:
            raise TransportError(f"HTTP {method} {url} failed: {exc}") from exc

    def _sync_http_request(
        self,
        method: str,
        url: str,
        body: bytes | None,
        content_type: str | None,
    ) -> bytes:
        from urllib import request as urlrequest

        headers = {}
        if content_type is not None:
            headers["Content-Type"] = content_type
        req = urlrequest.Request(url, data=body, headers=headers, method=method)
        with urlrequest.urlopen(req, timeout=self._open_timeout) as resp:
            data: bytes = resp.read()
            return data

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        """Yield raw event payloads from the SDK-owned WS reader.

        The reader starts in :meth:`open` and continuously drains the car's
        5 Hz state broadcasts even when no caller is iterating here.  This
        keeps command-only clients from filling the TCP window and starving
        firmware motor updates.
        """
        self._require_ws()
        while True:
            yield await self._incoming.get()

    def _start_reader(self) -> None:
        if self._reader_task is None or self._reader_task.done():
            self._reader_task = asyncio.create_task(self._reader_loop())

    async def _stop_reader(self) -> None:
        if self._reader_task is None:
            return
        self._reader_task.cancel()
        try:
            await self._reader_task
        except asyncio.CancelledError:
            pass
        finally:
            self._reader_task = None

    async def _reader_loop(self) -> None:
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
                _LOG.warning("bad JSON from car: %r", raw, exc_info=exc)
                continue
            self._push_incoming(payload)

    def _push_incoming(self, payload: dict[str, Any]) -> None:
        if self._incoming.full():
            try:
                self._incoming.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self._incoming.put_nowait(payload)
