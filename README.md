# hoymiles-g3-modbus

*AI slop disclaimer: this thing was written by deepseek-v4-flash-0731 with input from me.*

A small Python library for reading live telemetry from a **Hoymiles G3 hybrid inverter**
(HIT-G3 series, e.g. HIT-15L-G3) over Modbus TCP, asynchronously. It talks to the
DTS-WL-G3 stick that connects the inverter to your network.

The library knows the full register map of the inverter, reads all of it in a few large
bursts, and hands you live numbers as normal Python values — so you can build dashboards,
loggers, or home-automation feeds without touching Modbus yourself.
It is **read-only**: it never writes to the inverter.

## Tested on one specific setup

This library has **only been tested against one combination of hardware**:

- **Inverter:** Hoymiles **HIT-15L-G3**
- **Batteries:** 2 × Hoymiles **LB-16D-G3** (~32 kWh total)
- **Data stick:** Hoymiles **DTS-WL-G3**

It is written generically and *should* work with other G3 hybrid inverters, but every
other combination is unverified — register addresses, scales, and quirks can differ. Treat
anything outside the tested setup as "probably works, not confirmed".

> **How to reach it:** Modbus over TCP is only exposed through the **DTS-WL-G3's Ethernet
> interface** (not Wi-Fi, not USB). Point the library at that stick's IP address, e.g.
> `192.168.1.80:502`. The stick and your machine must be on the same network.


---

## What you get

- A list of ~145 named measurements (see "The measurements" below).
- Typed values with sensible units already applied (e.g. `54.0` instead of raw `540`).
- Convenient access: `inverter.battery.voltage`, `inverter["battery_soc"]`,
  `inverter.pv_total_energy`, and more.
- Automatic detection of what the unit exposes (whether a battery or grid meter is
  attached, how many MPPT strings it has, its model string).

---

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Requires Python 3.11+ and `pymodbus>=3.15`. (Use the `.venv` — your system Python is
likely "externally managed" and will refuse installs.)

---

## Quick start

```python
import asyncio
from hoymiles_g3_modbus_tcp import Inverter, InverterConfig

async def main():
    inv = Inverter(InverterConfig(host="192.168.1.80"))
    await inv.connect()

    info = await inv.detect()
    print("model:", info.inverter_model)          # "HIT-15L-G3"
    print("has battery:", info.has_battery)       # True
    print("capacity kWh:", info.battery_capacity_kwh)

    snapshot = await inv.poll()                   # reads all registers once
    print("battery SOC:", snapshot["battery_soc"])
    print("grid voltage A:", inv.grid_voltage_a)  # attribute access works too
    print("battery voltage:", inv.battery.voltage)  # convenience property

    await inv.close()

asyncio.run(main())
```

`poll()` does everything: it reads every known register (a handful of large block reads,
~2 seconds), caches the raw words in memory, and returns a snapshot dict with one entry
per measurement.

---

## The main pieces

| Thing | What it's for |
|---|---|
| `Inverter(config)` | The thing you talk to. One connection per inverter. |
| `InverterConfig` | Connection settings: `host`, `port` (502), `unit` (1), `timeout`, `max_block`, `poll_ranges`. |
| `InverterInfo` | What detection found: model string, `has_battery`, `has_grid_meter`, `pv_mppt_count`, `battery_capacity_kwh`. |
| `inverter.poll()` | Refresh everything and get a `{key: value}` snapshot. |
| `inverter.read("battery_soc")` / `inv["battery_soc"]` / `inv.battery_soc` | Three equivalent ways to read one value. |
| `inverter.battery`, `.pv`, `.grid`, ... | Grouped views of a family of measurements. |

### Grouped views

Each view holds a family of related measurements, and `get(key)` looks one up by name:

```python
inv.battery.soc            # battery state of charge, %
inv.battery.voltage        # battery voltage, V
inv.battery.current        # battery current, A (positive = discharging)
inv.battery.power          # battery power, W
inv.battery.capacity       # battery capacity, kWh

inv.pv.get("pv1_power")    # string 1 power, W
inv.energy.get("pv_total_energy")  # lifetime PV output, kWh
inv.energy.as_dict()       # every energy measurement as a dict
```

Groups: `battery`, `pv`, `grid`, `grid_meter`, `ac`, `backup`, `generator`, `energy`.

---

## Command-line probe

Quick way to see everything live:

```bash
.venv/bin/python -m hoymiles_g3_modbus_tcp --host 192.168.1.80
```

Prints the device info line, then one line per measurement: `key = value unit`.
Add `--poll 10` to re-read every 10 seconds until you press Ctrl-C.

---

## The measurements

The register catalog lives in `hoymiles_g3_modbus_tcp/registers.py` (transcribed from the reference
map). Highlights:

| Area | Examples |
|---|---|
| **Status / safety** | `workstatus`, firmware versions (`powerdsp_fm_ver`, `safetydsp_fm_ver`), `sw_fault`, `hw_fault`, DC-injection current |
| **PV** | `pv1_voltage`/`pv1_current`/`pv1_power` … `pv4_*`, `pv_total_energy` |
| **Battery** | `battery_soc`, `batt_voltage_bms`, `batt_current_bms`, `battery_capacity`, charge/discharge cutoffs, max charge/discharge current, cell temps |
| **Grid / AC** | per-phase grid voltage & frequency, inverter voltage/current/active/reactive power, backup (EPS) voltage/current/apparent/active power |
| **Grid meter** | meter link, per-phase meter current and grid power (import/export) |
| **Generator** | per-phase gen voltage/current/active power (nothing connected to this unit, so low values are normal) |
| **Energy** | lifetime and per-day energy: PV, battery charge/discharge, grid buy/sell, load use |

### Totals are computed, not read

Some "total" registers on this family return a junk sentinel value (they read `5` instead
of a real number). For those, the library **computes the total from its parts** instead
of reading the register:

| Measurement | How it's computed |
|---|---|
| `pv_total_power` | `pv1_power + pv2_power + pv3_power + pv4_power` |
| `bat_total_power` | equals `bat1_power_g3` (the real battery-power register) |
| `inv_active_power` | sum of inverter active power A + B + C |
| `inv_reactive_power` | sum of reactive A + B + C |
| `backup_apparent_power` | sum of apparent A + B + C |
| `backup_active_power` | sum of active A + B + C |

If any part is missing, the whole total is `None` rather than a guess. Trying to read the
raw word of a computed measurement (`inv.raw(...)`) returns `None`.

### Measurements intentionally left out

- `pe_voltage` and the battery/grid-meter **model strings** are not exposed — they were
  confirmed not to decode / not to exist in the register set.
- `load_energy_total` is dropped because it always reads zero on this hardware; use
  `load_energy_use` instead.

---

## Notes on the hardware (things to know)

- **How it reads:** one large block read per address range, up to 123 registers each.
  Total poll is ~2 seconds for the whole set. 124+ per request is not supported by the
  device.
- **Don't scatter single reads.** Good starts for block reads are fixed; the library's
  default `poll_ranges` already targets the safe ones. Only change `poll_ranges` if you
  know what you're doing — the dead zone `[1101, 1800)` returns no data.
- **One connection at a time.** Don't run two copies polling the same inverter at once.

---

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Covers decoding (signed/unsigned 16/32-bit, floats, scaled values, byte-swapped ASCII),
the block-read plan, and the computed-total behaviour.

---

## Reliability

Live-verified against a real HIT-15L-G3: model string and detection are exact, and a
single `poll()` returns in well under 4 seconds. If you change the register catalog, run
the unit tests before and after — they're fast and they protect the decode/read logic.
