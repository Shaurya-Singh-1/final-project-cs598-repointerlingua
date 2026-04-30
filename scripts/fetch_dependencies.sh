#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d PyBugHive ]]; then
  git clone https://github.com/PyBugHive/PyBugHive.git PyBugHive
fi

if [[ ! -d software-agents-course ]]; then
  git clone https://github.com/lingming/software-agents.git software-agents-course
fi

echo
echo "Dependency repos are available in:"
echo "  $ROOT/PyBugHive"
echo "  $ROOT/software-agents-course"
