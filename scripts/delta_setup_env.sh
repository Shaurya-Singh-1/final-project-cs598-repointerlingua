#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

module purge
module load cray-python

python3 -m pip install --user uv
"$HOME/.local/bin/uv" venv --python 3.11 .venv
source .venv/bin/activate
"$HOME/.local/bin/uv" pip install -e ".[gpu]"
"$HOME/.local/bin/uv" pip install pipenv

echo
echo "Environment ready. Activate it with:"
echo "  cd \"$ROOT\""
echo "  source .venv/bin/activate"
