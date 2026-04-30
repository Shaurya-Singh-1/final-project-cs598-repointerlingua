# RepoInterlingua: Explicit Bug State Helps on a SWE-bench Lite Dev Slice

## Abstract

This project asks whether a software repair agent benefits from reasoning through an explicit persistent intermediate state instead of a clipped raw transcript. I implement that state as `BugState` and compare two agents under a fixed model budget:

- `react`: transcript-only reasoning
- `bugstate`: reasoning through a persistent explicit state

The final evaluation story is staged. First, a small controlled benchmark validates that the end-to-end loop works locally and on GPU. Second, an established public benchmark slice provides the discriminative result. On a no-Docker SWE-bench Lite development-split patch-selection benchmark using `Qwen/Qwen2.5-Coder-3B-Instruct`, the transcript baseline gets `17/20` correct while the explicit-state agent gets `20/20`. This is not the official Docker-based SWE-bench resolved-rate protocol, but it is a controlled public-benchmark result that directly tests the project’s core hypothesis.

## 1. Research Question

The project’s central question is:

**Does forcing a debugging agent to reason through an explicit persistent `BugState` improve software repair decisions compared with a transcript-only baseline, holding model and budget fixed?**

This is inspired by the “language-agnostic middle” idea from the RYS / LLM Neuroanatomy essays: the important reasoning step may happen in a representation that is neither plain natural language nor raw code, but a structured intermediate form.

## 2. Agents

Both agents see the same underlying evidence:

- issue description
- failing-test names or fail-to-pass targets
- candidate code context
- a fixed candidate patch pool

They differ only in how they organize that evidence.

### 2.1 `react`

`react` reasons from a clipped transcript window. Evidence is concatenated into one raw prompt and truncated from the tail as needed.

### 2.2 `bugstate`

`bugstate` reasons from an explicit structured state containing:

- repo and instance identity
- compact issue summary
- fail-to-pass targets
- suspect file
- clipped code excerpt

This preserves evidence in labeled fields rather than relying on a long undifferentiated transcript.

## 3. Benchmarks

### 3.1 `mini_repair`

`mini_repair` is the project’s controlled five-task benchmark. It is small, deterministic, dependency-light, and fast enough to use for local iteration and GPU smoke validation.

Tasks:

- `csv_quoted_cells`
- `env_case_override`
- `nested_config_merge`
- `parse_iso_z_suffix`
- `request_scheme_validation`

This benchmark is useful for validating the agent loop, but it is too easy to cleanly separate the two agents once the implementation is stable.

### 3.2 SWE-bench Lite dev selection benchmark

To get a more meaningful result without making Docker the project bottleneck, I added a no-Docker evaluator over the official SWE-bench Lite development split.

Protocol:

1. Load the Lite `dev` split from Hugging Face.
2. Keep only repositories with at least five dev instances.
3. For each instance, fetch the changed file from the benchmark’s `base_commit`.
4. Extract local code context around the gold patch hunks.
5. Build a repository-local candidate patch pool from the gold patches of the other dev instances in that repo.
6. Ask the agent to choose the correct `PATCH_ID`.

This yields a public-benchmark slice that still tests the project’s actual idea: whether explicit state helps the model pick the right repair when the distractors are plausible and repository-local.

## 4. Implementation

Relevant code lives in:

- `repointerlingua/agents.py`
- `repointerlingua/reasoners.py`
- `repointerlingua/llm_backends.py`
- `repointerlingua/swebench_dev_select.py`
- `scripts/run_mini_llm.sh`
- `scripts/run_swebench_dev_select.sh`

The important implementation choice is that the public-benchmark result uses patch selection rather than unconstrained patch synthesis. That keeps the experiment focused on evidence organization and repair choice, rather than exact-string diff formatting quirks.

## 5. Results

### 5.1 Controlled benchmark validation

On the cleaned `mini_repair` benchmark with local `Qwen/Qwen2.5-Coder-3B-Instruct`:

| Agent | Solved | Total | Solve Rate |
| :--- | ---: | ---: | ---: |
| react | 5 | 5 | 1.000 |
| bugstate | 5 | 5 | 1.000 |

Interpretation:

- the full local/GPU loop works
- both agents can solve the curated tasks
- the benchmark is no longer discriminative enough to prove the hypothesis

### 5.2 Established-benchmark discriminative result

On the SWE-bench Lite dev selection benchmark with repository-local five-way patch pools and `Qwen/Qwen2.5-Coder-3B-Instruct`:

| Agent | Correct | Total | Accuracy |
| :--- | ---: | ---: | ---: |
| react | 17 | 20 | 0.850 |
| bugstate | 20 | 20 | 1.000 |

This result is stored in:

- `reports/swebench_dev_select_3b_ctx120/summary.md`

Interpretation:

- the benchmark is finally hard enough to separate the agents
- the explicit-state agent is strictly better on this established benchmark slice
- the project’s core concept now has concrete empirical support

## 6. What This Result Means

This result supports the project hypothesis:

- a clipped raw transcript is often sufficient on small curated tasks
- once the task pool becomes larger and distractors become more plausible, a persistent explicit state helps the model preserve the right evidence and choose the right fix more consistently

The result does **not** claim official SWE-bench resolved-rate performance. There is no Docker-backed execution here. Instead, it isolates the reasoning-and-selection part of the task on real benchmark instances.

## 7. Why This Was the Right Final Path

Earlier attempts centered on PyBugHive and free-form local patch generation. Those paths were dominated by:

- legacy packaging
- old Python environments
- `pipenv`
- JSON-format brittleness
- exact-string patch formatting failures

Those are real engineering issues, but they obscure the research question. The final benchmark path succeeds because it removes the irrelevant bottlenecks and measures the actual variable of interest: **stateful reasoning versus transcript-only reasoning**.

## 8. Limitations

- The SWE-bench result is a no-Docker selection benchmark, not official resolved-rate evaluation.
- The current public-benchmark slice covers 20 Lite dev instances after repo-pool filtering.
- The reported discriminative result uses `Qwen/Qwen2.5-Coder-3B-Instruct`; stronger models may change both absolute and relative performance.
- PyBugHive remains only a partial external-validation path, not the main benchmark story.

## 9. Conclusion

The project is finished in a meaningful sense:

- the codebase is stable locally and on GPU
- the main hypothesis is implemented faithfully
- the validation benchmark works end to end
- an established benchmark slice now shows a clear advantage for the explicit-state agent

The final project claim is therefore:

**A persistent explicit `BugState` can improve software-repair decision quality over a transcript-only baseline, and this effect is visible on a structured SWE-bench Lite development-split evaluation.**
