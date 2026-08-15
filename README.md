# hoymiles-g3-modbus-tcp

*AI slop disclaimer: this thing was written by deepseek-v4-flash-0731 with input from me.*

A small Python library for reading live telemetry from a **Hoymiles G3 hybrid inverter**
(HIT-G3 series, e.g. HIT-15L-G3) over Modbus TCP, asynchronously. It talks to the
DTS-WL-G3 stick that connects the inverter to your network.

The library knows the full register map of the inverter, reads all of it in a few large
bursts, and hands you live numbers as normal Python values.

It is currently **read-only**, and never writes to the inverter.

> **Connection note:** Modbus over TCP is only exposed through the **DTS-WL-G3's Ethernet
> interface** (not Wi-Fi). Point the library at that stick's IP address, on port 502.


This library has **only been tested against one combination of hardware**:

- **Inverter:** Hoymiles **HIT-15L-G3**
- **Batteries:** 2 × Hoymiles **LB-16D-G3** (~32 kWh total)
- **Data transfer stick:** Hoymiles **DTS-WL-G3**

It *should* work with other G3 hybrid inverters, but other combinations are unverified
(e.g. with different, non-Hoymiles BMSes).

---

## What you get

- A catalog of ~275 named fields (see "The measurements" below), including decoded
  status enums and fault bitmaps.
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

...or use PyPI package `hoymiles-g3-modbus-tcp`

Requires Python 3.11+ and `pymodbus>=3.13.1`.

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

`poll()` reads every known register (a few large block reads, ~4 seconds), caches the
raw words in memory, and returns a snapshot dict with one entry per measurement.
For faster refreshes of just the fast-changing values, see the tiered `poll_group("fast")`
below.

---

## The main pieces

| Thing | What it's for |
|---|---|
| `Inverter(config)` | The thing you talk to. One connection per inverter. |
| `InverterConfig` | Connection settings: `host`, `port` (502), `unit` (1), `timeout`, `max_block`, `poll_ranges`, `holding_ranges`. |
| `InverterInfo` | What detection found: model string, `has_battery`, `has_grid_meter`, `pv_mppt_count`, `battery_capacity_kwh`. |
| `inverter.poll()` / `poll_all()` | Refresh everything and get a `{key: value}` snapshot. |
| `inverter.poll_group("fast")` | Refresh just one group of registers (see tiered polling). |
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

### Tiered polling (`poll_group` / `poll_all`)

Everything is read by a single `poll()`, but you can also poll a **named group** of
registers so fast-changing statistics run often and slow ones rarely. This keeps a
Home Assistant integration lightweight: read the small `fast` group every few seconds
and everything else once a minute.

```python
snap = await inv.poll_group("fast")   # ~1.3 s: power/current/voltage, meters, energy+flows
snap = await inv.poll_all()           # ~4 s: every register (input + holding)
```

Each group is read as a small number of contiguous block reads (up to 123 registers per
request). Groups are built from the same safe block starts (`0`, `123`, `1800`, `2000`,
`30000`, …) — starting a block at the wrong address returns garbage, so these are fixed
and shared between groups.

Available groups (`hoymiles_g3_modbus_tcp.groups.group_names()`):

| Group | Req | Reads | Use `poll_group(...)` every |
|---|---|---|---|
| `fast` | 6 | PV, battery, grid/AC/EPS, meters, energy & flow counters, overview totals | 5–10 s |
| `energy` | 2 | lifetime & per-day energy counters | 60 s |
| `status` | 4 | work status codes, fault bitmaps, battery status | 60 s |
| `battery` | 1 | slow BMS params (SOH, capacity, cutoffs, limits) | 60 s |
| `diagnostics` | 2 | thermals, aux rails, fan speeds, isolation | 60 s |
| `settings` | 8 | read-only holding registers (GCF, EMS, SOC limits) | 60 s+ |

The cache persists across polls: `poll_group` only refreshes its group's registers and
leaves every other value at its last-known reading (registers never read yet stay
`None`). Groups may overlap; overlapping registers are simply read twice.

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

The register catalog lives in `hoymiles_g3_modbus_tcp/registers.py`. Highlights:

| Area | Examples |
|---|---|
| **Status / safety** | `workstatus`, firmware versions (`powerdsp_fm_ver`, `safetydsp_fm_ver`), `sw_fault`, `hw_fault`, DC-injection current, `pe_voltage`, isolation/residual |
| **PV** | `pv1_voltage`/`pv1_current`/`pv1_power` … `pv4_*`, per-string energy, `pv_total_energy` |
| **Battery** | `battery_soc`/`battery_soh`, `batt_voltage_bms`, `batt_current_bms`, `batt_power_bms`, `battery_capacity`, cutoffs, max charge/discharge current, cell temps, BMS work status |
| **Grid / AC** | per-phase grid voltage & frequency, inverter voltage/current/active/reactive power, backup (EPS) voltage/current/apparent/active power |
| **Grid meter** | meter link, per-phase L1n/L2n/L3n voltage, current, active/reactive power, power factor, plus the separate **PV meter** block |
| **Generator** | per-phase gen voltage/current/active power and energy (nothing connected to this unit, so low values are normal) |
| **Energy & flow** | lifetime and per-day energy per string/phase/flow, plus live power-flow registers (PV→battery/load/grid, load-from-PV) |
| **Status / overview** | system & battery work status (as enums), live power totals, and decoded fault bitmaps (DSP power/safety, ARM comm/peripheral/system, battery) |
| **Settings** | GCF, SOC range, battery power limits, EPS/PV-island mode, and the EMS block (`ems_mode` … power limits) |

Status enums (`workstatus`, `bat_type`, `ems_mode`, `machines_type`, …) decode to labels.
Fault bitmaps (`dsp_pwr_faults`, `dsp_safety_faults`, `arm_*_faults`, `battery_faults`)
return a list of the active fault labels (empty list = no faults).

**Grid power.** `grid_active_power_total` (2165) is measured at the inverter's grid
port; `meter_active_*` (1808/1814) is measured at the external RS485 grid meter. They're
two different instruments at two points, so the values can differ slightly. Use
`meter_active_total` for net import/export.

**Load power.** `load_power` is the sum of the three phases; `load_power_total` (2169)
appears to include inverter self-consumption (fans, losses).

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
| `load_power` | sum of `load_power_a + load_power_b + load_power_c` (the home load, see below) |

If any part is missing, the whole total is `None` rather than a guess. Trying to read the
raw word of a computed measurement (`inv.raw(...)`) returns `None`.

### Measurements intentionally left out

- The battery/grid-meter **model strings** are not exposed — they don't decode on this
  hardware.
- `load_energy_total` is dropped because it always reads zero on this hardware; use
  `load_energy_use` instead.
- `pv_ths_temp` (112) and `ext_fan_1..4_speed` (153-156) read the family's constant
  `5` junk-sentinel (real temps run 46-56 °C, fans are off), so they're not exposed.
- `pv_power` (2151, energy block) reads a constant `0` even while PV produces 10 kW;
  use `pv_total_power_eb` (2150) instead.

---

## Notes on the hardware (things to know)

- **How it reads:** one large block read per address range, up to 123 registers each
  (FC04 for telemetry, FC03 for the read-only holding-register settings). A full poll of
  the whole catalog takes ~4 s on the tested unit. 124+ per request is not supported by
  the device.
- **Don't scatter single reads.** Good starts for block reads are fixed; the library's
  default `poll_ranges` / `holding_ranges` already target the safe ones. Only change them
  if you know what you're doing — the dead zone `[1101, 1800)` returns no data.
- **Read-only, including settings.** All registers (including EMS/settings) are only
  read, never written.
- **One connection at a time.** Don't run two copies polling the same inverter at once.
- **Bad-read detection.** A block read that decodes to an obviously-ridiculous value
  (e.g. SoC 2005%, 1000 V) is re-read up to `read_retries` times (default 3) before the
  value is kept. Bounds are generous physical limits, so out-of-spec but plausible
  readings (e.g. 15200 W on a 15 kW unit) are not affected.

---

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Covers decoding (signed/unsigned 16/32-bit, floats, scaled values, byte-swapped ASCII),
the block-read plan, and the computed-total behaviour.

---

## Reliability

Live-verified against a real HIT-15L-G3: model string and detection are exact, the new
battery (1900) and meter (1800) blocks replicate the values of the old addresses they
replace, and a single `poll()` returns in ~4 s. Unsupported registers read as `None`.

---

## Acknowledgments

- [Kaluzaburza/Hoymiles_HIT_xxL_G3_ModBus](https://github.com/Kaluzaburza/Hoymiles_HIT_xxL_G3_ModBus) —
  the inverter register map this catalog is based on.
- [isjo-org/ha-hoymiles-modbus](https://github.com/isjo-org/ha-hoymiles-modbus) — the
  register map originally referenced.
