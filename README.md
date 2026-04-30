# FINAL PROJECT CS 598

RepoInterlingua is a research codebase for testing a RYS-inspired idea on software agents:

> Does forcing a debugging agent to reason through an explicit persistent `BugState` improve software repair compared with a transcript-only baseline?

The repository is now organized around a cleaner evaluation story:

- `benchmarks/mini_repair`: the primary controlled benchmark for the project
- optional real-world validation on `PyBugHive`
- optional future public-benchmark validation on SWE-bench Lite dev instances if Docker or Modal is available

## What is in this folder

- `repointerlingua/`: agents, reasoners, runtime, benchmark loaders, reporting, and training utilities
- `benchmarks/mini_repair/`: the primary benchmark for the project
- `configs/`: example configs
- `reports/`: reports and generated results
- `scripts/`: local and GPU experiment runners
- `software-agents-course/`: cloned reference material from the course repo
- `PyBugHive/`: optional cloned benchmark reference

## Recommended benchmark stack

For this project, the recommended order is:

1. run the deterministic smoke benchmark to validate the harness
2. run the LLM-backed `mini_repair` benchmark as the main quantitative result
3. use PyBugHive only as a qualitative or small-slice external validation path
4. treat SWE-bench Lite as an optional future public benchmark, not a day-one dependency

This keeps the main results focused on the agent architecture rather than old packaging or environment drift.

## Quick start

From this directory:

```bash
python3 -m repointerlingua.cli list-tasks
bash scripts/run_smoke.sh
```

## Main experiment

The main experiment is the LLM-backed `mini_repair` comparison:

```bash
bash scripts/run_mini_llm.sh
```

This runs:

- `react`
- `bugstate`

using:

- `reasoner=llm`
- `backend=transformers`
- `model=Qwen/Qwen2.5-Coder-7B-Instruct`

Outputs go to:

- `reports/mini_repair_qwen/summary.md`
- `reports/mini_repair_qwen/summary.json`

Override the defaults if needed:

```bash
MODEL=Qwen/Qwen2.5-Coder-7B-Instruct \
OUT=reports/mini_repair_custom \
TRANSCRIPT_WINDOW_CHARS=1200 \
MAX_PATCH_ATTEMPTS=2 \
bash scripts/run_mini_llm.sh
```

## Why `mini_repair` is primary

`mini_repair` is intentionally:

- deterministic
- dependency-light
- fast to run
- matched to the actual hypothesis

It lets us test whether a persistent `BugState` helps preserve and use debugging evidence across:

- issue text
- failing tests
- code snippets

without letting Docker, `pipenv`, or legacy repository setup dominate the experiment.

## Optional real-world validation

### PyBugHive

PyBugHive is still supported, but it is now considered optional validation rather than the backbone of the project.

Prepare a manifest:

```bash
python3 -m repointerlingua.cli prepare-pybughive \
  --dataset PyBugHive/dataset/pybughive_small.json \
  --output reports/pybughive_small_manifest.jsonl
```

Then run:

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

### SWE-bench Lite

SWE-bench Lite is a better long-term public benchmark target than PyBugHive, but the official evaluation flow depends on Docker or a cloud-backed evaluation path. This repo does not currently make SWE-bench Lite the primary path because the project should succeed without Docker-specific infrastructure.

## GPU path

For a GPU machine, the intended workflow is:

1. run `bash scripts/run_mini_llm.sh`
2. inspect `reports/mini_repair_qwen/summary.md`
3. optionally run a small PyBugHive validation slice
4. optionally export trajectories and fine-tune

On Delta, a convenience batch script is provided:

```bash
sbatch scripts/delta_mini_llm_compare.sbatch
```

## Project status

This repository is set up to be useful in three ways:

- it gives a complete local or GPU-run main benchmark
- it preserves an external-validation path for real-world bugs
- it can still be extended toward SWE-bench Lite or LoRA fine-tuning later
