#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

module purge
module reset
module load pytorch-conda/2.8

python3 -m venv --system-site-packages .venv-gpu
./.venv-gpu/bin/python3 -m ensurepip --upgrade || true
./.venv-gpu/bin/python3 -m pip install -U pip setuptools wheel
./.venv-gpu/bin/python3 -m pip install -e ".[gpu]"

echo
echo "Environment ready. Activate it with:"
echo "  cd \"$ROOT\""
echo "  source .venv-gpu/bin/activate"
