Issue: merging nested configuration blocks crashes when the override introduces a deeper nested key that is not present in the default config.

Observed behavior:
- loading user YAML with a new nested `project.tags.primary` entry raises an exception
- existing nested defaults should still be preserved

Expected behavior:
- if a nested key does not exist in the default config, treat that branch as an empty dictionary instead of crashing
