import unittest

from hoymiles_g3_modbus_tcp.decode import decode_ascii_string, decode_words


class TestDecodeWords(unittest.TestCase):
    def test_i16_negative(self):
        self.assertEqual(decode_words([0x8001], "I16"), -32767)

    def test_u16(self):
        self.assertEqual(decode_words([0x8001], "U16"), 0x8001)

    def test_i32_negative(self):
        self.assertEqual(decode_words([0xFFFF, 0xFFFE], "I32"), -2)

    def test_h32(self):
        self.assertEqual(decode_words([0x0000, 0x0100], "H32"), 256)

    def test_scale_after_decode(self):
        self.assertEqual(decode_words([540], "U16", 10), 54.0)

    def test_f32_zero(self):
        self.assertEqual(decode_words([0, 0], "F32"), 0.0)

    def test_f32_known(self):
        # 0x3F800000 == 1.0
        self.assertEqual(decode_words([0x3F80, 0x0000], "F32"), 1.0)

    def test_unknown_dtype(self):
        with self.assertRaises(ValueError):
            decode_words([1], "BOGUS")


class TestDecodeAsciiString(unittest.TestCase):
    def test_byte_swapped_hit(self):
        words = [0x4948, 0x2D54, 0x3531, 0x2D4C, 0x3347]
        self.assertEqual(decode_ascii_string(words, byte_swap=True), "HIT-15L-G3")

    def test_empty(self):
        self.assertEqual(decode_ascii_string([0x0000, 0x0101]), "")


if __name__ == "__main__":
    unittest.main()
