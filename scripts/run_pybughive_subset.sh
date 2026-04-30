#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODEL="${MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct}"
MANIFEST="${MANIFEST:-reports/pybughive_small_manifest.jsonl}"
OUT="${OUT:-reports/pybughive_runs}"

python3 -m repointerlingua.cli eval \
  --benchmark pybughive \
  --manifest "$MANIFEST" \
  --agent bugstate \
  --reasoner llm \
  --backend transformers \
  --model "$MODEL" \
  --output "$OUT"

echo
echo "PyBugHive eval command completed."
