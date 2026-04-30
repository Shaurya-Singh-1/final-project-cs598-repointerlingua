#!/bin/bash
#SBATCH --job-name=repointerlingua-smoke
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:20:00
#SBATCH --output=slurm-smoke-%j.out
#SBATCH --error=slurm-smoke-%j.err
#SBATCH --account=ACCOUNT_NAME

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

source .venv/bin/activate
bash scripts/run_smoke.sh
