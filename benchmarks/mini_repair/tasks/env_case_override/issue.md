Issue: environment variables should override defaults case-insensitively on Windows, but mixed-case keys currently fail to override.

Observed behavior:
- `Api_Key` does not override `API_KEY`
- users on Windows see default credentials even when the variable is present

Expected behavior:
- key matching should be case-insensitive for environment-like overrides
