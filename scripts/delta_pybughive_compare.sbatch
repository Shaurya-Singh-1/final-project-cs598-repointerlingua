#!/bin/bash
#SBATCH --job-name=repointerlingua-pybughive
#SBATCH --partition=gpuA40x4
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=1
#SBATCH --mem=48G
#SBATCH --time=08:00:00
#SBATCH --output=slurm-pybughive-%j.out
#SBATCH --error=slurm-pybughive-%j.err
#SBATCH --account=ACCOUNT_NAME

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

source .venv/bin/activate

if [[ ! -f reports/pybughive_small_manifest.jsonl ]]; then
  python3 -m repointerlingua.cli prepare-pybughive \
    --dataset PyBugHive/dataset/pybughive_small.json \
    --output reports/pybughive_small_manifest.jsonl
fi

python3 -m repointerlingua.cli compare \
  --benchmark pybughive \
  --manifest reports/pybughive_small_manifest.jsonl \
  --agents react bugstate \
  --reasoner llm \
  --backend transformers \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --output reports/pybughive_compare_qwen
