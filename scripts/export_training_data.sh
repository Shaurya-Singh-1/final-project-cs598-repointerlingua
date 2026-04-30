#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUNS="${1:-reports/local_results}"
OUT="${2:-reports/sft_data}"

python3 -m repointerlingua.cli export-sft --runs "$RUNS" --output "$OUT"

echo
echo "Export complete. Files are in $OUT"
