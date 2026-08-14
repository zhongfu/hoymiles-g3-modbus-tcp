"""Inverter facade: domain views + whole-inverter read/poll/snapshot API."""
from __future__ import annotations

import asyncio

from .cacher import RegisterCache
from .client import HoymilesClient, ModbusReadError
from .config import InverterConfig, detect_config
from .readplan import build_read_plan
from .registers import REGISTERS, REGISTERS_BY_ADDR, REGISTERS_BY_KEY


class DomainView:
    """Value accessor scoped to one register domain (e.g. ``inverter.battery``)."""

    def __init__(self, domain: str, cache: RegisterCache, by_key: dict):
        self._domain = domain
        self._cache = cache
        self._regs = [r for r in REGISTERS if r.domain == domain]

    def __getitem__(self, key):
        return self.get(key)

    def get(self, key, default=None):
        reg = REGISTERS_BY_KEY.get(key)
        if reg is None or reg.domain != self._domain:
            return default
        v = self._cache.value(reg)
        return default if v is None else v

    def as_dict(self) -> dict:
        return {r.key: self._cache.value(r) for r in self._regs}

    def __contains__(self, key):
        reg = REGISTERS_BY_KEY.get(key)
        return reg is not None and reg.domain == self._domain


class _BatteryView(DomainView):
    """Battery domain with human-readable convenience properties."""

    @property
    def soc(self):
        return self.get("battery_soc")

    @property
    def voltage(self):
        return self.get("batt_voltage_bms")

    @property
    def current(self):
        return self.get("batt_current_bms")

    @property
    def power(self):
        return self.get("bat1_power_g3")

    @property
    def capacity(self):
        return self.get("battery_capacity")


class Inverter:
    """Async reader for a single Hoymiles G3 hybrid inverter (one connection)."""

    def __init__(self, config: InverterConfig):
        self._config = config
        self._client = HoymilesClient(
            config.host, port=config.port, unit=config.unit, timeout=config.timeout
        )
        self._cache = RegisterCache(REGISTERS_BY_KEY, REGISTERS_BY_ADDR)
        self._lock = asyncio.Lock()
        self._info = None

    async def connect(self) -> None:
        await self._client.connect()

    async def detect(self):
        info = await detect_config(self._client)
        self._info = info
        return info

    async def poll(self) -> dict:
        async with self._lock:
            raw = {}
            for addr, count in build_read_plan(
                self._config.poll_ranges, self._config.max_block
            ):
                try:
                    words = await self._client.read_input(addr, count)
                    for i, v in enumerate(words):
                        raw[addr + i] = v
                except ModbusReadError:
                    for i in range(count):
                        raw.setdefault(addr + i, None)
            self._cache.update(raw)
        return self.snapshot()

    def read(self, key):
        reg = REGISTERS_BY_KEY.get(key)
        return None if reg is None else self._cache.value(reg)

    def raw(self, key):
        reg = REGISTERS_BY_KEY.get(key)
        if reg is None or reg.source:
            return None
        return self._cache.raw_addr(reg.addr)

    def __getitem__(self, key):
        return self.read(key)

    def __getattr__(self, name):
        reg = REGISTERS_BY_KEY.get(name)
        if reg is not None:
            return self._cache.value(reg)
        raise AttributeError(name)

    def snapshot(self) -> dict:
        return {r.key: self._cache.value(r) for r in REGISTERS}

    @property
    def device_info(self):
        if self._info is None:
            raise RuntimeError("call detect() before accessing device_info")
        return self._info

    @property
    def battery(self):
        return _BatteryView("battery", self._cache, REGISTERS_BY_KEY)

    def _view(self, domain):
        return DomainView(domain, self._cache, REGISTERS_BY_KEY)

    @property
    def pv(self):
        return self._view("pv")

    @property
    def grid(self):
        return self._view("grid")

    @property
    def grid_meter(self):
        return self._view("grid_meter")

    @property
    def ac(self):
        return self._view("ac")

    @property
    def generator(self):
        return self._view("generator")

    @property
    def energy(self):
        return self._view("energy")

    async def close(self) -> None:
        await self._client.close()
