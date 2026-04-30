import unittest

from minilib.csvparse import parse_csv_line


class CsvParseTests(unittest.TestCase):
    def test_quoted_name_keeps_internal_comma(self):
        parsed = parse_csv_line("\"Ng, David\",researcher,active")
        self.assertEqual(parsed, ["Ng, David", "researcher", "active"])


if __name__ == "__main__":
    unittest.main()
