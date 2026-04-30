import unittest

from minilib.dates import parse_timestamp


class DateParsingTests(unittest.TestCase):
    def test_trailing_z_is_utc(self):
        parsed = parse_timestamp("2024-01-02T03:04:05Z")
        self.assertIsNotNone(parsed.tzinfo)
        self.assertEqual(parsed.utcoffset().total_seconds(), 0)


if __name__ == "__main__":
    unittest.main()
