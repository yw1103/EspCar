"""CLI: ``python -m deskcar_orch`` runs the auto-dock loop."""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from deskcar_orch.config import load_config
from deskcar_orch.runtime import Orchestrator

_LOG = logging.getLogger("deskcar_orch")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-c", "--config", default="configs/default.yaml",
        help="YAML config file (default: configs/default.yaml)",
    )
    p.add_argument(
        "--car-host", default=None,
        help="override config car_host (skip discovery)",
    )
    p.add_argument(
        "--calibrate", action="store_true",
        help="print the homography matrix and exit",
    )
    p.add_argument(
        "--dock", action="store_true",
        help="force the docking sequence immediately (useful for testing)",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


async def _amain(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if args.car_host is not None:
        cfg = cfg.with_overrides(car_host=args.car_host)
    if args.calibrate:
        _LOG.info("using config: %s", cfg)
        return 0
    orch = Orchestrator(cfg, force_dock=args.dock)
    await orch.run()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    try:
        return asyncio.run(_amain(args))
    except KeyboardInterrupt:
        _LOG.info("interrupted; exiting")
        return 0


if __name__ == "__main__":
    sys.exit(main())
