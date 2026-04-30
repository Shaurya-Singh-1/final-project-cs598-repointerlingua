Issue: invalid request paths containing a colon are currently treated like valid URLs, while `data:` URLs should continue to work.

Observed behavior:
- `/foo:bar` is accepted even though it has no scheme
- browser-style `data:` payload URLs are valid and should not be rejected

Expected behavior:
- only real scheme-prefixed URLs should pass validation
- `data:` URLs remain accepted
