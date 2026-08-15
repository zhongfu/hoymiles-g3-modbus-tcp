"""Async Modbus TCP client wrapper (FC04 input registers)."""
from __future__ import annotations

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException


class ModbusReadError(Exception):
    def __init__(self, addr: int, count: int, reason: str = ""):
        super().__init__(f"read_input({addr}, {count}) failed: {reason}")
        self.addr = addr
        self.count = count
        self.reason = reason


class HoymilesClient:
    """Owns a single Modbus TCP connection to the DTU / inverter."""

    def __init__(self, host: str, port: int = 502, unit: int = 1, timeout: float = 3.0):
        self._client = AsyncModbusTcpClient(host, port=port, timeout=timeout)
        self._unit = unit

    async def connect(self) -> None:
        await self._client.connect()

    async def read_input(self, addr: int, count: int) -> list[int]:
        return await self._transact(self._client.read_input_registers, addr, count)

    async def read_holding(self, addr: int, count: int) -> list[int]:
        return await self._transact(self._client.read_holding_registers, addr, count)

    async def _transact(self, rfn, addr: int, count: int) -> list[int]:
        """Run one register read, reconnecting on a dropped session.

        If pymodbus reports the connection as lost, close + reconnect and
        retry the read once. A real Modbus error (``ModbusReadError``) or a
        second connection failure propagates to the caller.
        """
        try:
            rr = await rfn(addr, count=count, device_id=self._unit)
        except ConnectionException:
            await self._reconnect()
            rr = await rfn(addr, count=count, device_id=self._unit)
        if rr.isError():
            raise ModbusReadError(addr, count, str(rr))
        return list(rr.registers)

    async def _reconnect(self) -> None:
        self._client.close()
        connected = await self._client.connect()
        if not connected:
            raise ConnectionException("reconnect failed")

    async def close(self) -> None:
        self._client.close()
