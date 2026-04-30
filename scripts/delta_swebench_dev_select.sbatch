#!/bin/bash
#SBATCH --job-name=repointerlingua-swebench-dev
#SBATCH --partition=gpuA40x4
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=1
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=slurm-swebench-dev-%j.out
#SBATCH --error=slurm-swebench-dev-%j.err
#SBATCH --account=ACCOUNT_NAME

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

PYTHON_BIN=./.venv-gpu/bin/python bash scripts/run_swebench_dev_select.sh
