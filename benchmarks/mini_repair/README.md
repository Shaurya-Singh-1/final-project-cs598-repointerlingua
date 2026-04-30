# Mini Repair Benchmark

This benchmark is intentionally small, deterministic, and dependency-light. Its purpose is to validate the research pipeline locally before bigger runs on PyBugHive.

Each task contains:

- `issue.md`: a bug report
- `repo/`: a tiny Python repository with one bug
- `task.json`: evaluation metadata and a hidden reference patch

The five tasks were chosen to stress different kinds of cross-format evidence:

- stack trace + code only
- issue text + test failure + code
- API format mismatch
- platform-specific behavior
- parser bug with quoted text

The local pattern reasoner uses the hidden patch metadata to validate the control flow and evaluation harness. The LLM reasoner ignores the hidden patch and only sees the issue, logs, and code.
