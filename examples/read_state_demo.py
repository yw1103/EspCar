#!/usr/bin/env python3
"""Connect to a DeskCar, read the latest telemetry, then exit.

Usage::

    pip install -e ./sdk
    python examples/read_state_demo.py                       # auto-discover
    python examples/read_state_demo.py --host 192.168.4.1   # skip discovery
    python examples/read_state_demo.py --drive 2.0          # then drive 2 s

This is the smallest runnable end-to-end example.  No fake transport,
no mocks; it talks to a real car.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from deskcar import Chassis, DeskCarError, StateSnapshot

_LOG = logging.getLogger("read_state_demo")


async def _run(host: str | None, drive_seconds: float) -> int:
    if host is None:
        _LOG.info("discovering DeskCar on the LAN (2 s timeout)...")
        try:
            car = await Chassis.discover_first(timeout=2.0)
        except DeskCarError as exc:
            print(f"discovery failed: {exc}", file=sys.stderr)
            return 2
    else:
        car = Chassis.from_host(host)

    print(f"connecting to {car.info.base_url}")
    await car.connect()
    try:
        snap: StateSnapshot = await car.read_state()
        print("--- first state frame ---")
        print(f"  uptime   : {snap.ts} ms")
        print(f"  battery  : {snap.v} V, {snap.i} mA, {snap.soc} %")
        print(f"  charge   : {snap.charge.name}")
        print(f"  wifi     : {snap.wifi}")
        print(f"  pwm cap  : {snap.speed}")
        print(f"  expansion: {[d.address for d in snap.exp]}")

        if drive_seconds > 0:
            print(f"--- driving forward for {drive_seconds:.1f} s ---")
            await car.drive(left=150, right=150)
            try:
                await asyncio.sleep(drive_seconds)
            finally:
                await car.stop()
            print("stopped")
    finally:
        await car.close()
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", help="skip discovery; use this IP")
    p.add_argument("--drive", type=float, default=0.0,
                   help="after reading state, drive forward for N seconds")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    return asyncio.run(_run(args.host, args.drive))


if __name__ == "__main__":
    raise SystemExit(main())