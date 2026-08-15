import asyncio
import unittest

from hoymiles_g3_modbus_tcp.config import InverterConfig
from hoymiles_g3_modbus_tcp.inverter import Inverter
from hoymiles_g3_modbus_tcp.registers import REGISTERS_BY_ADDR, REGISTERS_BY_KEY
from hoymiles_g3_modbus_tcp.validation import REGISTER_BOUNDS, block_is_plausible

def _block(at: dict):
    """Build a word block starting at address 0 (values at absolute addresses).

    Every bounded register present is filled with a mid-range plausible value so
    that neighbors never trip the check; ``at`` overrides specific addresses.
    """
    size = max(at) + 1
    words = [0] * size
    for addr, reg in REGISTERS_BY_ADDR.items():
        lo, hi = REGISTER_BOUNDS.get(reg.key, (None, None))
        if hi is None or addr >= size:
            continue
        words[addr] = int((lo + hi) / 2 * reg.scale)
    for i, v in at.items():
        words[i] = v
    return words


def _addr(key):
    return REGISTERS_BY_KEY[key].addr


def _soc_range():
    a = _addr("battery_soc")
    return (a, a + 1)


class TestBlockIsPlausible(unittest.TestCase):
    def test_battery_soc_implausible(self):
        words = _block({_addr("battery_soc"): 2005})  # the cited live failure
        self.assertFalse(block_is_plausible(0, len(words), words))

    def test_battery_soc_good(self):
        words = _block({_addr("battery_soc"): 68, _addr("battery_soh"): 95})
        self.assertTrue(block_is_plausible(0, len(words), words))

    def test_grid_voltage_plausible_scale(self):
        # raw 2428 with scale 10 -> 242.8 V
        words = _block({_addr("grid_voltage_a"): 2428})
        self.assertTrue(block_is_plausible(0, len(words), words))

    def test_huge_unbounded_power_no_false_positive(self):
        # pv1_power is intentionally unbounded; absurd raw must not trip.
        words = _block({_addr("pv1_power"): 3_000_000})
        self.assertTrue(block_is_plausible(0, len(words), words))

    def test_missing_word_not_bad(self):
        words = _block({_addr("battery_soc"): None})
        self.assertTrue(block_is_plausible(0, len(words), words))

    def test_empty_trivial_block_good(self):
        self.assertTrue(block_is_plausible(0, 1, [0]))

    def test_empty_bounds_always_true(self):
        words = _block({_addr("battery_soc"): 2005})
        self.assertTrue(block_is_plausible(0, len(words), words, bounds={}))

    def test_grid_frequency_bounds(self):
        hi = _block({_addr("grid_frequency"): 9700})   # 97.00 Hz
        self.assertFalse(block_is_plausible(0, len(hi), hi))
        ok = _block({_addr("grid_frequency"): 5000})   # 50.00 Hz
        self.assertTrue(block_is_plausible(0, len(ok), ok))


class TestReadRangesRetry(unittest.TestCase):
    def _inv(self, retries=3):
        return Inverter(InverterConfig(host="0.0.0.0", port=502, read_retries=retries))

    def test_implausible_then_good_retries_once(self):
        calls = []

        async def stub_read(addr, count):
            calls.append((addr, count))
            return [2005] if len(calls) == 1 else [68]

        async def run():
            inv = self._inv()
            return await inv._read_ranges((_soc_range(),), stub_read)

        raw = asyncio.run(run())
        self.assertEqual(len(calls), 2)
        self.assertEqual(raw[_addr("battery_soc")], 68)

    def test_plausible_first_read_no_retry(self):
        calls = []

        async def stub_read(addr, count):
            calls.append((addr, count))
            return [68]

        async def run():
            inv = self._inv()
            return await inv._read_ranges((_soc_range(),), stub_read)

        raw = asyncio.run(run())
        self.assertEqual(len(calls), 1)
        self.assertEqual(raw[_addr("battery_soc")], 68)

    def test_persistent_implausible_keeps_last(self):
        # Exhausted retries: last (still implausible) block is kept, transparently.
        calls = []

        async def stub_read(addr, count):
            calls.append((addr, count))
            return [2005]

        async def run():
            inv = self._inv()
            return await inv._read_ranges((_soc_range(),), stub_read)

        raw = asyncio.run(run())
        self.assertEqual(len(calls), 3)  # read_retries = 3 attempts
        self.assertEqual(raw[_addr("battery_soc")], 2005)


if __name__ == "__main__":
    unittest.main()
