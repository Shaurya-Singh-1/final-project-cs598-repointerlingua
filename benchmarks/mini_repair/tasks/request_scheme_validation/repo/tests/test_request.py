import unittest

from minilib.request import validate_url


class RequestValidationTests(unittest.TestCase):
    def test_relative_paths_with_colons_still_raise(self):
        with self.assertRaises(ValueError):
            validate_url("/foo:bar")

    def test_data_urls_are_allowed(self):
        value = validate_url("data:text/plain;base64,SGVsbG8=")
        self.assertEqual(value, "data:text/plain;base64,SGVsbG8=")


if __name__ == "__main__":
    unittest.main()
