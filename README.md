# FINAL PROJECT CS 598

RepoInterlingua is a research codebase for testing a RYS-inspired idea on software agents:

> Does forcing a debugging agent to reason through an explicit persistent `BugState` improve software repair compared with a transcript-only baseline?

The repository is now organized around a cleaner evaluation story:

- `benchmarks/mini_repair`: the fast controlled harness-validation benchmark
- `SWE-bench Lite dev` oracle patch selection: the primary discriminative benchmark
- optional real-world validation on `PyBugHive`
- optional future official SWE-bench execution if Docker or Modal is available

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
2. run the LLM-backed `mini_repair` benchmark in patch-selection mode to validate the local/GPU loop
3. run the SWE-bench Lite dev patch-selection benchmark as the main discriminative result
4. use PyBugHive only as a qualitative or small-slice external validation path

This keeps the main results focused on the agent architecture rather than Docker, old packaging, or environment drift.

## Quick start

From this directory:

```bash
python3 -m repointerlingua.cli list-tasks
bash scripts/run_smoke.sh
```

## Main experiment

First run the LLM-backed `mini_repair` comparison:

```bash
bash scripts/run_mini_llm.sh
```

This runs:

- `react`
- `bugstate`
- `repair-mode=select`

using:

- `reasoner=llm`
- `backend=transformers`
- `model=Qwen/Qwen2.5-Coder-3B-Instruct` by default for local runs

Outputs go to:

- `reports/mini_repair_qwen_3b/summary.md`
- `reports/mini_repair_qwen_3b/summary.json`

Override the defaults if needed:

```bash
MODEL=Qwen/Qwen2.5-Coder-7B-Instruct \
OUT=reports/mini_repair_custom \
TRANSCRIPT_WINDOW_CHARS=1200 \
MAX_PATCH_ATTEMPTS=2 \
bash scripts/run_mini_llm.sh
```

Then run the established-benchmark slice:

```bash
bash scripts/run_swebench_dev_select.sh
```

This runs a SWE-bench Lite development-split evaluation with:

- repo-grouped oracle patch pools
- `react` and `bugstate`
- fixed model and prompt budget
- no Docker dependency

Default output:

- `reports/swebench_dev_select_3b_ctx120/summary.md`
- `reports/swebench_dev_select_3b_ctx120/summary.json`

The current reference run with `Qwen/Qwen2.5-Coder-3B-Instruct` achieved:

- `react`: `17/20`
- `bugstate`: `20/20`

## Why `mini_repair` exists

`mini_repair` is intentionally:

- deterministic
- dependency-light
- fast to run
- matched to the actual hypothesis

It lets us test whether a persistent `BugState` helps preserve and use debugging evidence across:

- issue text
- failing tests
- code snippets

without letting Docker, `pipenv`, legacy repository setup, or brittle free-form patch generation dominate the experiment.

## Why SWE-bench Lite dev is now primary

The key project question is whether a persistent explicit state helps an agent make better repair decisions than a clipped raw transcript. The SWE-bench Lite dev selection benchmark is the first setting in this repository that is both:

- established enough to be recognizable outside the project
- difficult enough to separate `react` and `bugstate`

It is not the official Docker-based SWE-bench resolved-rate protocol. Instead, it is a no-Docker oracle patch-selection protocol over the official Lite dev instances, grouped by repository so each task must be distinguished from closely related distractor patches.

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

This repository now includes a no-Docker SWE-bench Lite dev evaluator:

```bash
python3 -m repointerlingua.swebench_dev_select \
  --backend transformers \
  --model Qwen/Qwen2.5-Coder-3B-Instruct \
  --output reports/swebench_dev_select_3b_ctx120 \
  --agents react bugstate \
  --transcript-window-chars 1200 \
  --code-context-radius 120
```

The official Docker-backed SWE-bench evaluation path is still future work. The current evaluator is designed to prove the core concept under a recognized benchmark slice without making Docker the blocker for the project.

## GPU path

For a GPU machine, the intended workflow is:

1. run `bash scripts/run_mini_llm.sh`
2. run `bash scripts/run_swebench_dev_select.sh`
3. inspect `reports/swebench_dev_select_3b_ctx120/summary.md`
4. optionally run a small PyBugHive validation slice
5. optionally export trajectories and fine-tune

On Delta, a convenience batch script is provided:

```bash
sbatch scripts/delta_mini_llm_compare.sbatch
```

## Project status

This repository is set up to be useful in four ways:

- it gives a fast local or GPU harness-validation benchmark
- it gives a discriminative SWE-bench Lite dev benchmark without Docker
- it preserves an external-validation path for real-world bugs
- it can still be extended toward SWE-bench Lite or LoRA fine-tuning later
