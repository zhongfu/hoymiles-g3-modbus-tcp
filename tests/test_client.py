import asyncio
import unittest

from pymodbus.exceptions import ConnectionException

from hoymiles_g3_modbus_tcp.client import HoymilesClient, ModbusReadError


class _Result:
    def isError(self):
        return False
    registers = []


class _Err:
    def isError(self):
        return True


class _FakeClient:
    """Stand-in for the pymodbus AsyncModbusTcpClient."""
    def __init__(self):
        self.reads = []
        self.close_calls = 0
        self.connect_calls = 0
        self.fail_times = 0
        self.connect_ok = True
        self.result = _Result()

    async def read_input_registers(self, address, count=0, device_id=0):
        self.reads.append((address, count, device_id))
        if self.fail_times > 0:
            self.fail_times -= 1
            raise ConnectionException("Not connected")
        return self.result

    def close(self):
        self.close_calls += 1

    async def connect(self):
        self.connect_calls += 1
        return self.connect_ok


def make_client(fake):
    c = HoymilesClient.__new__(HoymilesClient)
    c._client = fake
    c._unit = 1
    return c


class TestReconnectOnDisconnect(unittest.TestCase):
    def test_reconnect_and_retry_after_disconnect(self):
        fake = _FakeClient()
        fake.fail_times = 1
        c = make_client(fake)
        out = asyncio.run(c.read_input(10, 5))
        self.assertEqual(out, [])
        # close + reconnect happened, and the read was retried
        self.assertEqual(fake.close_calls, 1)
        self.assertEqual(fake.connect_calls, 1)
        self.assertEqual(fake.reads, [(10, 5, 1), (10, 5, 1)])

    def test_no_reconnect_when_connection_healthy(self):
        fake = _FakeClient()
        c = make_client(fake)
        asyncio.run(c.read_input(10, 5))
        self.assertEqual(fake.close_calls, 0)
        self.assertEqual(fake.connect_calls, 0)
        self.assertEqual(fake.reads, [(10, 5, 1)])

    def test_second_disconnect_propagates(self):
        fake = _FakeClient()
        fake.fail_times = 2  # first raise -> reconnect -> second raise -> propagate
        c = make_client(fake)
        with self.assertRaises(ConnectionException):
            asyncio.run(c.read_input(10, 5))
        self.assertEqual(fake.connect_calls, 1)

    def test_modbus_read_error_does_not_reconnect(self):
        fake = _FakeClient()
        fake.result = _Err()
        c = make_client(fake)
        with self.assertRaises(ModbusReadError):
            asyncio.run(c.read_input(10, 5))
        self.assertEqual(fake.close_calls, 0)
        self.assertEqual(fake.connect_calls, 0)

    def test_reconnect_failure_propagates(self):
        fake = _FakeClient()
        fake.fail_times = 1
        fake.connect_ok = False
        c = make_client(fake)
        with self.assertRaises(ConnectionException):
            asyncio.run(c.read_input(10, 5))


if __name__ == "__main__":
    unittest.main()
