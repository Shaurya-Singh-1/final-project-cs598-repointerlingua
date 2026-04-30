#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

MODEL="${MODEL:-Qwen/Qwen2.5-Coder-3B-Instruct}"
OUT="${OUT:-reports/mini_repair_qwen_3b}"
TRANSCRIPT_WINDOW_CHARS="${TRANSCRIPT_WINDOW_CHARS:-1200}"
MAX_PATCH_ATTEMPTS="${MAX_PATCH_ATTEMPTS:-2}"

"$PYTHON_BIN" -m repointerlingua.cli compare \
  --benchmark mini_repair \
  --agents react bugstate \
  --reasoner llm \
  --backend transformers \
  --model "$MODEL" \
  --output "$OUT" \
  --repair-mode select \
  --transcript-window-chars "$TRANSCRIPT_WINDOW_CHARS" \
  --max-patch-attempts "$MAX_PATCH_ATTEMPTS"

echo
echo "Mini benchmark LLM run complete. See $OUT/summary.md"
