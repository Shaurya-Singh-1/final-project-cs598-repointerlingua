#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

BACKEND="${BACKEND:-transformers}"
MODEL="${MODEL:-Qwen/Qwen2.5-Coder-3B-Instruct}"
OUT="${OUT:-reports/swebench_dev_select_3b_ctx120}"
TRANSCRIPT_WINDOW_CHARS="${TRANSCRIPT_WINDOW_CHARS:-1200}"
CODE_CONTEXT_RADIUS="${CODE_CONTEXT_RADIUS:-120}"
MIN_REPO_POOL_SIZE="${MIN_REPO_POOL_SIZE:-5}"
LIMIT_ARGS=()
if [[ -n "${LIMIT:-}" ]]; then
  LIMIT_ARGS=(--limit "$LIMIT")
fi

cmd=(
  "$PYTHON_BIN" -m repointerlingua.swebench_dev_select
  --backend "$BACKEND"
  --model "$MODEL"
  --output "$OUT"
  --agents react bugstate
  --transcript-window-chars "$TRANSCRIPT_WINDOW_CHARS"
  --code-context-radius "$CODE_CONTEXT_RADIUS"
  --min-repo-pool-size "$MIN_REPO_POOL_SIZE"
)
if [[ -n "${LIMIT:-}" ]]; then
  cmd+=(--limit "$LIMIT")
fi

"${cmd[@]}"

echo
echo "SWE-bench Lite dev selection run complete. See $OUT/summary.md"
