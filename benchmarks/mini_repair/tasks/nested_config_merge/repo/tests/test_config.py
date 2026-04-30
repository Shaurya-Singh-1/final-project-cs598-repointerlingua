import unittest

from minilib.config import merge_configs


class MergeConfigTests(unittest.TestCase):
    def test_new_nested_branch_is_merged_without_crashing(self):
        default = {
            "author": "example",
            "project": {
                "description": "demo",
            },
        }
        overwrite = {
            "project": {
                "tags": {
                    "primary": "first",
                }
            }
        }
        result = merge_configs(default, overwrite)
        self.assertEqual(result["project"]["description"], "demo")
        self.assertEqual(result["project"]["tags"]["primary"], "first")


if __name__ == "__main__":
    unittest.main()
