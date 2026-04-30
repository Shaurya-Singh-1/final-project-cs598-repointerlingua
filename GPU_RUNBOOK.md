# GPU Runbook

This runbook is for a separate Linux GPU machine.

## 1. Copy the project

Copy the entire `FINAL PROJECT CS 598` folder to the GPU machine.

Then fetch the external repos:

```bash
bash scripts/fetch_dependencies.sh
```

## 2. Create an environment

Recommended on Delta:

```bash
cd "FINAL PROJECT CS 598"
module purge
module load cray-python
python3 -m pip install --user uv
~/.local/bin/uv venv --python 3.11 .venv
source .venv/bin/activate
~/.local/bin/uv pip install -e ".[gpu]"
~/.local/bin/uv pip install pipenv
```

If you want OpenAI API support too:

```bash
pip install -e ".[gpu,openai]"
```

## 3. Prepare a PyBugHive manifest

The repo already includes a small manifest at [pybughive_small_manifest.jsonl](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/reports/pybughive_small_manifest.jsonl), but you can regenerate it:

```bash
python3 -m repointerlingua.cli prepare-pybughive \
  --dataset PyBugHive/dataset/pybughive_small.json \
  --output reports/pybughive_small_manifest.jsonl
```

## 4. Run the real-bug evaluation

Hugging Face backend example:

```bash
python3 -m repointerlingua.cli eval \
  --benchmark pybughive \
  --manifest reports/pybughive_small_manifest.jsonl \
  --agent bugstate \
  --reasoner llm \
  --backend transformers \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --output reports/pybughive_bugstate_qwen
```

Baseline:

```bash
python3 -m repointerlingua.cli eval \
  --benchmark pybughive \
  --manifest reports/pybughive_small_manifest.jsonl \
  --agent react \
  --reasoner llm \
  --backend transformers \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --output reports/pybughive_react_qwen
```

## 5. Export trajectories for training

```bash
python3 -m repointerlingua.cli export-sft \
  --runs reports/pybughive_bugstate_qwen \
  --output reports/sft_data
```

Expected outputs:

- `reports/sft_data/state_updates.jsonl`
- `reports/sft_data/patch_generation.jsonl`

## 6. Fine-tune with LoRA

Patch-generation stage:

```bash
python3 -m repointerlingua.cli train-lora \
  --train-file reports/sft_data/patch_generation.jsonl \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --output-dir reports/lora_patch_model \
  --epochs 1
```

You can also train on state updates:

```bash
python3 -m repointerlingua.cli train-lora \
  --train-file reports/sft_data/state_updates.jsonl \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --output-dir reports/lora_state_model \
  --epochs 1
```

## 7. Recommended ablations

- `react` vs `bugstate`
- same model, same manifest, same transcript window, different agent architecture
- pre-fine-tuning vs post-fine-tuning
- small PyBugHive manifest first, then expand to the full dataset

## 8. Practical notes

- The current Mac does not have `docker` or `nvidia-smi`, so large-scale evaluation was intentionally staged for a different machine.
- PyBugHive install steps can be heavy and project-specific; the runner captures install logs inside each task run directory.
- Start with `pybughive_small.json` before expanding to the full dataset.
- On Delta, use `accounts` to find the correct allocation name; GPU allocations usually end with `-gpu` according to the official Delta docs.
