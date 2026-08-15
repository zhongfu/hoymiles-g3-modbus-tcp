import unittest

from hoymiles_g3_modbus_tcp.groups import GROUPS, group_names


class TestPollGroups(unittest.TestCase):
    def test_known_groups_and_all(self):
        self.assertIn("fast", GROUPS)
        self.assertIn("energy", GROUPS)
        self.assertIn("status", GROUPS)
        self.assertIn("battery", GROUPS)
        self.assertIn("diagnostics", GROUPS)
        self.assertIn("settings", GROUPS)
        self.assertIn("all", GROUPS)

    def test_group_names_exclude_all(self):
        self.assertEqual(
            group_names(),
            ["fast", "energy", "status", "battery",
             "diagnostics", "settings"],
        )

    def test_settings_group_is_holding_only(self):
        in_ranges, hold_ranges = GROUPS["settings"]
        self.assertEqual(in_ranges, ())
        self.assertTrue(hold_ranges)

    def test_fast_group_is_input_only(self):
        in_ranges, hold_ranges = GROUPS["fast"]
        self.assertTrue(in_ranges)
        self.assertEqual(hold_ranges, ())

    def test_all_covers_everything(self):
        all_in, all_hold = GROUPS["all"]
        self.assertTrue(all_in)
        self.assertTrue(all_hold)


if __name__ == "__main__":
    unittest.main()
