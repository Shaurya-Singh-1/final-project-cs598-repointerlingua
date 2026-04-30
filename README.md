# FINAL PROJECT CS 598

RepoInterlingua is a complete end-to-end research project for testing a RYS-inspired idea on software agents:

> Does forcing a software debugging agent to reason through an explicit, persistent, language-agnostic middle representation improve bug-fixing performance?

The project is designed in two layers:

- `benchmarks/mini_repair`: a local, dependency-light benchmark that runs on this Mac and always gives us smoke-test results.
- `PyBugHive` integration: a real-bug adapter and experiment pipeline for larger GPU-backed runs on a separate Linux machine.

The central method is a `BugState` interlingua. Instead of letting the agent jump directly from raw issue text and test logs to a patch, the proposed agent repeatedly translates observations into a structured state, reasons over that state, and only then proposes edits.

## What is in this folder

- `repointerlingua/`: the Python package with agents, benchmark loaders, runtime, training export, GPU fine-tuning hooks, and CLI.
- `benchmarks/mini_repair/`: five synthetic but realistic Python bug-fix tasks for local validation.
- `configs/`: example local and GPU configs.
- `reports/`: report materials and generated local results.
- `scripts/`: convenience wrappers for local smoke runs and GPU experiments.
- `software-agents-course/`: optional cloned reference material from the CS 598 course repo.
- `PyBugHive/`: optional cloned benchmark reference.

## Fetch dependencies

Clone the external reference repos when needed:

```bash
bash scripts/fetch_dependencies.sh
```

## Quick start

From this directory:

```bash
python3 -m repointerlingua.cli list-tasks
python3 -m repointerlingua.cli compare --benchmark mini_repair --agents react bugstate --reasoner pattern --output reports/local_results
```

Or use the wrapper:

```bash
bash scripts/run_smoke.sh
```

## Expected local behavior

The local smoke benchmark is intentionally tiny and deterministic. It is not the final research claim. Its job is to verify:

- the benchmark loader works
- the workspace copy/apply/evaluate loop works
- the explicit-state agent works end to end
- result files and summaries are generated
- the same framework is ready for bigger PyBugHive runs

## GPU path

For a GPU machine, the intended workflow is:

1. Prepare a PyBugHive manifest:

```bash
python3 -m repointerlingua.cli prepare-pybughive \
  --dataset PyBugHive/dataset/pybughive_small.json \
  --output reports/pybughive_small_manifest.jsonl
```

2. Run the bugstate agent with a local Hugging Face model backend:

```bash
python3 -m repointerlingua.cli eval \
  --benchmark pybughive \
  --manifest reports/pybughive_small_manifest.jsonl \
  --agent bugstate \
  --reasoner llm \
  --backend transformers \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --output reports/pybughive_runs
```

3. Export successful trajectories for supervised fine-tuning:

```bash
python3 -m repointerlingua.cli export-sft \
  --runs reports/pybughive_runs \
  --output reports/sft_data
```

4. Fine-tune on a GPU machine:

```bash
python3 -m repointerlingua.cli train-lora \
  --train-file reports/sft_data/patch_generation.jsonl \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --output-dir reports/lora_patch_model
```

## Project status

This repository is set up to be immediately useful in three ways:

- you can run a complete local experiment on this computer
- you can scale the same code to larger GPU experiments
- you can keep refining the prompts, backends, and benchmark mix without rewriting the framework
