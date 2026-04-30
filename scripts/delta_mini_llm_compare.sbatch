#!/bin/bash
#SBATCH --job-name=repointerlingua-mini
#SBATCH --partition=gpuA40x4
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=1
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=slurm-mini-%j.out
#SBATCH --error=slurm-mini-%j.err
#SBATCH --account=ACCOUNT_NAME

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

if [[ -f .venv-gpu/bin/activate ]]; then
  source .venv-gpu/bin/activate
else
  source .venv/bin/activate
fi
bash scripts/run_mini_llm.sh
