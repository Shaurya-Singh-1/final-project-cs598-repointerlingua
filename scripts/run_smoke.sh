#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

"$PYTHON_BIN" -m repointerlingua.cli compare \
  --benchmark mini_repair \
  --agents react bugstate \
  --reasoner pattern \
  --output reports/local_results

echo
echo "Smoke run complete. See reports/local_results/summary.md"
