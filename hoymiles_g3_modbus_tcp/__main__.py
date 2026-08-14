"""CLI probe for the Hoymiles G3 library.

Usage:
    python -m hoymiles_g3_modbus_tcp [--host H] [--port P] [--unit U] [--poll N]
"""
from __future__ import annotations

import argparse
import asyncio

from .config import InverterConfig
from .inverter import Inverter
from .registers import REGISTERS_BY_KEY


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


async def _run_once(inv: Inverter) -> None:
    info = inv.device_info
    print(
        f"model={info.inverter_model} battery={info.has_battery} "
        f"grid_meter={info.has_grid_meter} mppt={info.pv_mppt_count} "
        f"capacity_kwh={info.battery_capacity_kwh}"
    )
    snapshot = await inv.poll()
    for r in REGISTERS_BY_KEY.values():
        v = snapshot.get(r.key)
        suffix = f" {r.unit}" if r.unit else ""
        print(f"{r.key} = {_fmt(v)}{suffix}")


async def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="hoymiles_g3_modbus_tcp")
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--unit", type=int, default=1)
    ap.add_argument("--poll", type=float, default=0.0, help="repeat poll every N s")
    args = ap.parse_args(argv)

    cfg = InverterConfig(host=args.host, port=args.port, unit=args.unit)
    inv = Inverter(cfg)
    await inv.connect()
    try:
        await inv.detect()
        await _run_once(inv)
        if args.poll > 0:
            while True:
                await asyncio.sleep(args.poll)
                await inv.poll()
                print(f"--- poll at {args.poll}s ---")
    finally:
        await inv.close()


if __name__ == "__main__":
    asyncio.run(main())
