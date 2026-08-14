import unittest

from hoymiles_g3_modbus_tcp.cacher import RegisterCache
from hoymiles_g3_modbus_tcp.registers import REGISTERS_BY_ADDR, REGISTERS_BY_KEY


class TestComputedTotals(unittest.TestCase):
    def setUp(self):
        self.cache = RegisterCache(REGISTERS_BY_KEY, REGISTERS_BY_ADDR)

    def test_pv_total_is_sum_of_strings(self):
        self.cache.update({29: 100, 32: 200, 35: 50, 38: 50})
        self.assertEqual(self.cache.value(REGISTERS_BY_KEY["pv_total_power"]), 400)

    def test_inv_active_total_is_phase_sum(self):
        self.cache.update({74: 500, 75: 300, 76: 200})
        self.assertEqual(
            self.cache.value(REGISTERS_BY_KEY["inv_active_power"]), 1000
        )

    def test_bat_total_tracks_i32_power(self):
        # bat1_power_g3 is an I32 spanning regs 50-51 (hi word first).
        self.cache.update({50: 0, 51: 1000})
        self.assertEqual(
            self.cache.value(REGISTERS_BY_KEY["bat_total_power"]), 1000
        )

    def test_partial_source_yields_none(self):
        self.cache.update({74: 500})  # missing b and c
        self.assertIsNone(
            self.cache.value(REGISTERS_BY_KEY["inv_active_power"])
        )

    def test_totals_are_computed_not_address_decoded(self):
        # Junk at the total's own register address is ignored.
        self.cache.update({73: 5, 74: 100, 75: 200, 76: 300})
        self.assertEqual(
            self.cache.value(REGISTERS_BY_KEY["inv_active_power"]), 600
        )


if __name__ == "__main__":
    unittest.main()
