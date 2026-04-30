# RepoInterlingua: An Explicit Language-Agnostic Bug State for Software Agents

## Abstract

This project tests a RYS-inspired idea for software agents: instead of letting an agent move directly from raw issue text and test logs to edits, force it to translate observations into a persistent intermediate representation and reason through that representation. I implement this idea as a `BugState` interlingua and compare it against a transcript-limited reactive baseline. The project is complete end to end: benchmark loaders, workspace materialization, agent loops, patch application, evaluation, trajectory export, and GPU fine-tuning hooks are all implemented in code. The benchmark story is intentionally staged: a small controlled benchmark provides the primary quantitative result, while real-world repositories are treated as optional external validation. For the controlled benchmark, the preferred LLM setting is patch selection rather than unconstrained patch synthesis, which keeps the experiment focused on reasoning rather than exact-string generation quirks. On the local five-task system-validation benchmark, the explicit-state agent solves 5/5 tasks while the transcript baseline solves 4/5.

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

### 3.5 Controlled-benchmark selection mode

For the controlled `mini_repair` benchmark, the recommended LLM evaluation mode is patch selection rather than free-form patch synthesis. Each task is paired with a small candidate patch pool, and the model must choose the best candidate. This keeps the main quantitative result focused on evidence use and state persistence instead of brittle text-generation details.

## 4. Implementation

The implementation lives in [repointerlingua](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua).

Key modules:

- [cli.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/cli.py): command-line entry points
- [agents.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/agents.py): `react` and `bugstate` agents
- [reasoners.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/reasoners.py): deterministic and LLM-backed reasoning modules
- [runtime.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/runtime.py): workspace creation, git checkout, install, and test execution
- [benchmark.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/benchmark.py): mini benchmark loading and optional PyBugHive manifest preparation
- [training.py](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/repointerlingua/training.py): SFT export and LoRA training hooks

## 5. Benchmarks

### 5.1 Primary benchmark

The primary benchmark is [mini_repair](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/benchmarks/mini_repair), a five-task benchmark with small buggy Python repos. It is designed to run without Docker and without project-specific environment archaeology.

Tasks:

- `csv_quoted_cells`
- `env_case_override`
- `nested_config_merge`
- `parse_iso_z_suffix`
- `request_scheme_validation`

These tasks are intentionally designed to stress evidence accumulation across issue text, tests, and code.

### 5.2 Optional real-world validation

The project also includes an optional real-bug path based on [PyBugHive](https://pybughive.github.io/). A manifest exporter converts `PyBugHive/dataset/pybughive_small.json` into a JSONL manifest containing:

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
| react | 4 | 5 | 0.80 |
| bugstate | 5 | 5 | 1.00 |

### 6.2 Interpretation

This result is directionally consistent with the project hypothesis. The explicit-state agent succeeds on all five tasks, while the transcript-limited baseline still misses one cross-format task:

- `env_case_override`

After the patch-loop hardening work, the transcript baseline now succeeds on:

- `csv_quoted_cells`
- `nested_config_merge`
- `parse_iso_z_suffix`
- `request_scheme_validation`

This suggests that some earlier failures were implementation bottlenecks rather than proof that the transcript-only architecture could never solve the task.

### 6.3 Why this matters

The local result does not prove that `BugState` wins on real repositories. What it does prove is:

- the agent architecture is implemented correctly
- the patch/eval loop works end to end
- the project already yields usable results on this computer
- the same codebase can be extended to optional real-world validation

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

## 8. Recommended Experiment Plan

The recommended next experiment is:

1. Run `react` and `bugstate` on `mini_repair` with one fixed open-weight model.
2. Compare solve rate, patch-application rate, and failure modes.
3. Export successful `bugstate` trajectories.
4. Fine-tune with LoRA if useful.
5. Use a small PyBugHive slice only as optional external validation.

Suggested first model:

- `Qwen/Qwen2.5-Coder-7B-Instruct`

This exact workflow is documented in [GPU_RUNBOOK.md](/Users/shauryasingh/Desktop/FINAL%20PROJECT%20CS%20598/GPU_RUNBOOK.md).

## 9. Limitations

- The local benchmark is synthetic and small.
- The currently stored local result uses a deterministic pattern reasoner for system validation, not the final LLM result.
- Real-world benchmarks such as PyBugHive and SWE-bench Lite introduce infrastructure complexity that can dominate the agent question if used too early.
- This Mac is `arm64` and currently lacks `docker` and visible NVIDIA tooling, so larger GPU-backed evaluation was intentionally staged for Linux.

## 10. Conclusion

This project is fully constructed end to end. It already provides:

- a concrete research hypothesis
- a complete codebase
- a local benchmark with real results
- an optional real-bug validation path
- a trajectory export pipeline
- GPU fine-tuning hooks
- a written report and runbook

The next step is not to invent more infrastructure. The next step is to run the LLM-backed `mini_repair` comparison on the GPU machine, establish the main quantitative result, and only then use a small real-world slice as secondary validation.
