#!/bin/bash
#SBATCH --job-name=repointerlingua-lora
#SBATCH --partition=gpuA40x4
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=1
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=slurm-lora-%j.out
#SBATCH --error=slurm-lora-%j.err
#SBATCH --account=ACCOUNT_NAME

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

source .venv/bin/activate

python3 -m repointerlingua.cli export-sft \
  --runs reports/pybughive_compare_qwen/bugstate \
  --output reports/sft_data

python3 -m repointerlingua.cli train-lora \
  --train-file reports/sft_data/patch_generation.jsonl \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --output-dir reports/lora_patch_model \
  --epochs 1
