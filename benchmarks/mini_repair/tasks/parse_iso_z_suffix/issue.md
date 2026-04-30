Issue: API timestamps emitted by browsers often end with a trailing `Z`, but our parser returns a naive datetime instead of an explicit UTC-aware one.

Observed behavior:
- parsing `2024-01-02T03:04:05Z` returns a datetime with no timezone information

Expected behavior:
- trailing `Z` should produce an explicit UTC timezone
