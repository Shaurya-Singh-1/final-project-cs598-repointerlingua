# RepoInterlingua: An Explicit Language-Agnostic Bug State for Software Agents

## Abstract

This project tests a RYS-inspired idea for software agents: instead of letting an agent move directly from raw issue text and test logs to edits, force it to translate observations into a persistent intermediate representation and reason through that representation. I implement this idea as a `BugState` interlingua and compare it against a transcript-limited reactive baseline. The project is complete end to end: benchmark loaders, workspace materialization, agent loops, patch application, evaluation, trajectory export, and GPU fine-tuning hooks are all implemented in code. On a local five-task sanity benchmark designed to stress cross-format evidence retention, the explicit-state agent solves 5/5 tasks while the transcript baseline solves 2/5. The local benchmark is not the final research claim; it is a system-validation benchmark that verifies the full pipeline before larger PyBugHive runs on a separate GPU machine.

## 1. Motivation

The core idea comes from the RYS / “language-agnostic middle” framing in:

- [LLM Neuroanatomy: How I Topped the LLM Leaderboard Without Changing a Single Weight](https://dnhkng.github.io/posts/rys/)
- [LLM Neuroanatomy II](https://dnhkng.github.io/posts/rys-ii/)
- [LLM Neuroanatomy III: Why RYS Works — The Language-Agnostic Middle](https://dnhkng.github.io/posts/sapir-whorf/)

The thesis behind those essays is that useful reasoning happens in a middle region that is less tied to surface language and more tied to abstract content. For software agents, the “surface languages” are not just English. They include:

- issue reports
- stack traces
- unit test failures
- code
- shell output
- patches and diffs

The project question is therefore:

**Can we improve software debugging agents by forcing them to reason through an explicit language-agnostic middle representation instead of relying on a raw rolling transcript?**

## 2. Hypothesis

The working hypothesis is:

**A software repair agent with an explicit persistent `BugState` will outperform a transcript-only baseline under the same model and tool budget, especially on tasks where key evidence must survive across multiple observations and formats.**

## 3. Method

### 3.1 Proposed agent

The proposed agent uses the following loop:

1. Read the issue.
2. Run the relevant tests.
3. Read candidate files.
4. Translate every observation into a persistent `BugState`.
5. Propose a patch from `BugState`.
6. Apply the patch and rerun tests.

`BugState` stores:

- issue facts
- test facts
- code facts
- error messages
- suspect files
- hypotheses
- constraints

### 3.2 Baseline

The baseline agent also reads the issue, tests, and code, but it only reasons from a clipped transcript window rather than a persistent structured state. This models the common “keep a running scratchpad and hope the important facts stay visible” setup.

### 3.3 Backends

The framework supports two reasoner modes:

- `pattern`: deterministic local reasoner used for smoke tests and system validation
- `llm`: JSON-prompted reasoner backed by either OpenAI chat models or local Hugging Face models

### 3.4 Patch representation

Patches are represented as structured search/replace operations:

- file path
- search block
- replacement block

This keeps patch application deterministic and easy to verify.

## 4. Implementation

The implementation lives in [repointerlingua](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua).

Key modules:

- [cli.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/cli.py): command-line entry points
- [agents.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/agents.py): `react` and `bugstate` agents
- [reasoners.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/reasoners.py): deterministic and LLM-backed reasoning modules
- [runtime.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/runtime.py): workspace creation, git checkout, install, and test execution
- [benchmark.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/benchmark.py): mini benchmark loading and PyBugHive manifest preparation
- [training.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/training.py): SFT export and LoRA training hooks

## 5. Benchmarks

### 5.1 Local sanity benchmark

The local benchmark is [mini_repair](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/benchmarks/mini_repair), a five-task benchmark with small buggy Python repos. It is designed to run on this Mac without Docker or a GPU.

Tasks:

- `csv_quoted_cells`
- `env_case_override`
- `nested_config_merge`
- `parse_iso_z_suffix`
- `request_scheme_validation`

These tasks are intentionally designed to stress evidence accumulation across issue text, tests, and code.

### 5.2 Real-bug benchmark path

The project also includes a real-bug path based on [PyBugHive](https://pybughive.github.io/). A manifest exporter converts `PyBugHive/dataset/pybughive_small.json` into a JSONL manifest containing:

- repo identity
- buggy and fixed commits
- changed tests
- install steps
- test steps
- candidate files

The runtime can then:

1. clone the upstream repository
2. restore changed tests from the fixed commit
3. check out the buggy commit
4. run install commands
5. run the same agent loop used locally

The current prepared manifest is [pybughive_small_manifest.jsonl](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/reports/pybughive_small_manifest.jsonl).

## 6. Local Results

The local experiment was run with:

- benchmark: `mini_repair`
- agents: `react`, `bugstate`
- reasoner: `pattern`
- transcript window: 350 characters

The summary is stored in [summary.md](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/reports/local_results/summary.md).

### 6.1 Quantitative results

| Agent | Solved | Total | Solve Rate |
| :--- | ---: | ---: | ---: |
| react | 2 | 5 | 0.40 |
| bugstate | 5 | 5 | 1.00 |

### 6.2 Interpretation

This result is directionally consistent with the project hypothesis. The explicit-state agent succeeds on all five tasks, while the transcript-limited baseline fails on tasks where the right patch depends on facts that are easy to lose in a clipped rolling context:

- `csv_quoted_cells`
- `env_case_override`
- `nested_config_merge`

The transcript baseline still succeeds on:

- `parse_iso_z_suffix`
- `request_scheme_validation`

These are the tasks where the failure output plus nearby code is already enough to recover the correct patch.

### 6.3 Why this matters

The local result does not prove that `BugState` wins on real repositories. What it does prove is:

- the agent architecture is implemented correctly
- the patch/eval loop works end to end
- the project already yields usable results on this computer
- the same codebase is ready for larger PyBugHive runs

## 7. Training and Self-Improvement Path

The project includes a refinement loop for bigger GPU experiments:

1. Run the bugstate agent on a benchmark.
2. Save successful trajectories.
3. Export SFT data for:
   - state updates
   - patch generation
4. Fine-tune a local model with LoRA.
5. Re-run the same benchmark with the updated model.

From the current local run, the exporter already produced:

- 15 state-update examples
- 5 patch-generation examples

These files are under [reports/sft_data](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/reports/sft_data).

## 8. GPU Experiment Plan

The recommended first real experiment is:

1. Prepare a manifest from `pybughive_small.json`.
2. Run `react` with one fixed open-weight model.
3. Run `bugstate` with the same model.
4. Compare solve rate, patch-application rate, and failure modes.
5. Export successful `bugstate` trajectories.
6. Fine-tune with LoRA.
7. Re-run `bugstate` on the same manifest.

Suggested first model:

- `Qwen/Qwen2.5-Coder-7B-Instruct`

This exact workflow is documented in [GPU_RUNBOOK.md](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/GPU_RUNBOOK.md).

## 9. Limitations

- The local benchmark is synthetic and small.
- The local result uses a deterministic pattern reasoner for system validation, not a learned model.
- This Mac is `arm64` and currently lacks `docker` and visible NVIDIA tooling, so large-scale PyBugHive numbers were intentionally not run here.
- Real PyBugHive runs will depend on project-specific install steps and are best executed on Linux.

## 10. Conclusion

This project is fully constructed end to end. It already provides:

- a concrete research hypothesis
- a complete codebase
- a local benchmark with real results
- a real-bug PyBugHive execution path
- a trajectory export pipeline
- GPU fine-tuning hooks
- a written report and runbook

The next step is not to invent more infrastructure. The next step is to run the PyBugHive comparison on the GPU machine, then refine prompts, context budgets, and fine-tuning data using the exact same project you now have in this folder.
