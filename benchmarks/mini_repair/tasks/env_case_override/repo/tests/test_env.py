import unittest

from minilib.env import merge_env


class EnvMergeTests(unittest.TestCase):
    def test_mixed_case_env_key_overrides_default(self):
        defaults = {"API_KEY": "default", "REGION": "us"}
        overrides = {"Api_Key": "secret"}
        merged = merge_env(defaults, overrides)
        self.assertEqual(merged["API_KEY"], "secret")


if __name__ == "__main__":
    unittest.main()
