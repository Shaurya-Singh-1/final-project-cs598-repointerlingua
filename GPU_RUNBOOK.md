# GPU Runbook

This runbook is for a separate Linux GPU machine such as Delta.

## 1. Copy the project

Copy the project folder to the GPU machine, then fetch external references if needed:

```bash
bash scripts/fetch_dependencies.sh
```

## 2. Create a GPU environment

Recommended on Delta:

```bash
cd "FINAL PROJECT CS 598"
module purge
module reset
module load pytorch-conda/2.8

python3 -m venv --system-site-packages .venv-gpu
./.venv-gpu/bin/python3 -m ensurepip --upgrade || true
./.venv-gpu/bin/python3 -m pip install -U pip setuptools wheel
./.venv-gpu/bin/python3 -m pip install -e ".[gpu]"
```

Verify:

```bash
./.venv-gpu/bin/python3 - <<'PY'
import sys, torch
print("python_exe:", sys.executable)
print("torch_version:", torch.__version__)
print("cuda_available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("gpu_name:", torch.cuda.get_device_name(0))
PY
```

## 3. Run the validation benchmark

Start with the LLM-backed `mini_repair` comparison:

```bash
./.venv-gpu/bin/python3 -m repointerlingua.cli compare \
  --benchmark mini_repair \
  --agents react bugstate \
  --reasoner llm \
  --backend transformers \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --output reports/mini_repair_qwen \
  --repair-mode select \
  --transcript-window-chars 1200 \
  --max-patch-attempts 2
```

Or use the wrapper:

```bash
bash scripts/run_mini_llm.sh
```

Expected outputs:

- `reports/mini_repair_qwen/summary.md`
- `reports/mini_repair_qwen/summary.json`

## 4. Run the discriminative benchmark

The main discriminative experiment is the SWE-bench Lite dev oracle patch-selection benchmark:

```bash
PYTHON_BIN=./.venv-gpu/bin/python \
MODEL=Qwen/Qwen2.5-Coder-3B-Instruct \
OUT=reports/swebench_dev_select_3b_ctx120 \
bash scripts/run_swebench_dev_select.sh
```

Expected outputs:

- `reports/swebench_dev_select_3b_ctx120/summary.md`
- `reports/swebench_dev_select_3b_ctx120/summary.json`

Reference result from the local run:

- `react`: `17/20`
- `bugstate`: `20/20`

## 5. Delta batch submission

For a standard Delta batch job:

```bash
sbatch scripts/delta_mini_llm_compare.sbatch
```

Update the account placeholder first:

```bash
sed -i 's/ACCOUNT_NAME/bgvu-delta-gpu/g' scripts/delta_mini_llm_compare.sbatch
```

For the SWE-bench dev selection benchmark:

```bash
sed -i 's/ACCOUNT_NAME/bgvu-delta-gpu/g' scripts/delta_swebench_dev_select.sbatch
sbatch scripts/delta_swebench_dev_select.sbatch
```

## 6. Optional real-world validation

### PyBugHive

Use PyBugHive only as secondary validation, not as the main result path.

Prepare the manifest:

```bash
./.venv-gpu/bin/python3 -m repointerlingua.cli prepare-pybughive \
  --dataset PyBugHive/dataset/pybughive_small.json \
  --output reports/pybughive_small_manifest.jsonl
```

Run a small validation slice:

```bash
./.venv-gpu/bin/python3 -m repointerlingua.cli eval \
  --benchmark pybughive \
  --manifest reports/pybughive_small_manifest.jsonl \
  --agent bugstate \
  --reasoner llm \
  --backend transformers \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --output reports/pybughive_bugstate_qwen
```

### SWE-bench Lite official execution

The repo now includes a no-Docker SWE-bench Lite dev evaluator, which is the recommended main result path. The official Docker-backed SWE-bench execution flow remains a later extension unless your machine has a working Docker or Modal path.

## 7. Optional training loop

Export successful trajectories:

```bash
./.venv-gpu/bin/python3 -m repointerlingua.cli export-sft \
  --runs reports/mini_repair_qwen/bugstate \
  --output reports/sft_data
```

Fine-tune patch generation:

```bash
./.venv-gpu/bin/python3 -m repointerlingua.cli train-lora \
  --train-file reports/sft_data/patch_generation.jsonl \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --output-dir reports/lora_patch_model \
  --epochs 1
```

## 8. Recommended reporting order

1. `mini_repair` LLM comparison in patch-selection mode
2. SWE-bench Lite dev patch-selection comparison
3. error analysis on failed public-benchmark tasks
4. one or a few real-world validation cases
5. optional fine-tuning extension
