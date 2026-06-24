#!/usr/bin/env python3
"""Keyboard teleop for a DeskCar chassis.

WASD/arrows = drive, Space = stop, q = quit.  The car only moves while
a key is held: the loop releases the motors the instant the key is
released, so a stalled terminal cannot run away with the chassis.

Requires the optional ``keyboard`` package on Linux/macOS; on Windows
we use ``msvcrt`` so no extra deps are needed.

::

    pip install -e ./sdk
    python examples/keyboard_teleop.py
    python examples/keyboard_teleop.py --host 192.168.4.1 --speed 180
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import sys
from collections.abc import Iterator

from deskcar import Chassis, DeskCarError

_LOG = logging.getLogger("keyboard_teleop")


# --- platform key reader --------------------------------------------------

def _keypresses_unix() -> Iterator[str]:
    """Blocking generator yielding one char per keypress on Linux/macOS."""
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if not ch:
                return
            yield ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _keypresses_win() -> Iterator[str]:
    """Non-blocking generator yielding one char per keypress on Windows."""
    import msvcrt  # type: ignore[import-not-found]

    while True:
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):  # function / arrow prefix
            ch2 = msvcrt.getwch()
            yield {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT"}.get(ch2, "?")
        else:
            yield ch


def keypresses() -> Iterator[str]:
    if sys.platform.startswith("win"):
        return _keypresses_win()
    return _keypresses_unix()


# --- keymap ---------------------------------------------------------------

SPEED_BY_KEY = {
    "w": ( 1,  1), "UP":    ( 1,  1),
    "s": (-1, -1), "DOWN":  (-1, -1),
    "a": (-1,  1), "LEFT":  (-1,  1),
    "d": ( 1, -1), "RIGHT": ( 1, -1),
}


# --- main loop ------------------------------------------------------------

async def _run(host: str | None, speed: int) -> int:
    if host is None:
        try:
            car = await Chassis.discover_first(timeout=2.0)
        except DeskCarError as exc:
            print(f"discovery failed: {exc}", file=sys.stderr)
            return 2
    else:
        car = Chassis.from_host(host)

    print(f"connecting to {car.info.base_url} (PWM cap = {speed})")
    await car.connect()
    # The firmware broadcasts state frames at 5 Hz.  Teleop sends commands
    # but does not display telemetry, so drain inbound frames in the background.
    drain_task = car.start_event_drain()
    await car.set_speed_cap(speed)
    print("controls: w/a/s/d or arrows = drive, space = stop, q = quit")
    try:
        for key in keypresses():
            key = key.lower()
            if key in ("q", "x", "\x03"):  # q / x / Ctrl-C
                break
            if key in (" ", "space"):
                await car.stop()
                print("stop")
                continue
            kv = SPEED_BY_KEY.get(key)
            if kv is None:
                continue
            l, r = kv[0] * speed, kv[1] * speed
            await car.drive(left=l, right=r)
        await car.stop()
    finally:
        drain_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await drain_task
        with contextlib.suppress(Exception):
            await car.close()
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", help="skip discovery; use this IP")
    p.add_argument("--speed", type=int, default=180,
                   help="global PWM cap 0..255 (default 180)")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    logging.basicConfig(level=logging.WARNING)
    try:
        return asyncio.run(_run(args.host, args.speed))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
