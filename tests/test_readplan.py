import unittest

from hoymiles_g3_modbus_tcp.readplan import build_read_plan


class TestBuildReadPlan(unittest.TestCase):
    def test_single_range(self):
        self.assertEqual(
            build_read_plan([(0, 50)], 123), [(0, 50)]
        )

    def test_default_plan(self):
        self.assertEqual(
            build_read_plan([(0, 369), (1000, 1123)], 123),
            [(0, 123), (123, 123), (246, 123), (1000, 123)],
        )

    def test_full_default_ranges(self):
        self.assertEqual(
            build_read_plan([(0, 369), (1000, 1123), (2000, 2246)], 123),
            [(0, 123), (123, 123), (246, 123),
             (1000, 123), (2000, 123), (2123, 123)],
        )

    def test_off_by_one_hi_exclusive(self):
        self.assertEqual(build_read_plan([(0, 123)], 123), [(0, 123)])


if __name__ == "__main__":
    unittest.main()
