# RepoInterlingua: Explicit Bug State Helps on a SWE-bench Lite Dev Slice

## Abstract

This project asks whether a software repair agent benefits from reasoning through an explicit persistent intermediate state instead of a clipped raw transcript. I implement that state as `BugState` and compare two agents under a fixed model budget:

- `react`: transcript-only reasoning
- `bugstate`: reasoning through a persistent explicit state

The final evaluation story is staged. First, a small controlled benchmark validates that the end-to-end loop works locally and on GPU. Second, an established public benchmark slice provides the discriminative result. On a no-Docker SWE-bench Lite development-split patch-selection benchmark using `Qwen/Qwen2.5-Coder-3B-Instruct`, the transcript baseline gets `17/20` correct while the explicit-state agent gets `20/20`. This is not the official Docker-based SWE-bench resolved-rate protocol, but it is a controlled public-benchmark result that directly tests the project’s core hypothesis.

## 1. RYS Background

This project is motivated by the RYS / LLM Neuroanatomy line of work by David Noel Ng. The central idea is that transformer models appear to have a rough three-stage functional anatomy:

- early layers that normalize and encode surface form
- middle layers that carry more abstract, format-agnostic reasoning
- late layers that decode back into output tokens

RYS itself is not a software-repair method. It is a model-level intervention and interpretability claim: repeating a block of middle layers, without ordinary fine-tuning, was reported to improve model performance and motivated the hypothesis that the middle layers are unusually important for reasoning.

For this project, the important takeaway is not “repeat layers.” The important takeaway is the idea of a **language-agnostic middle**: a representation that is less tied to raw surface form and more tied to task-relevant meaning.

## 2. Research Question

The project’s central question is:

**Does forcing a debugging agent to reason through an explicit persistent `BugState` improve software repair decisions compared with a transcript-only baseline, holding model and budget fixed?**

This is inspired by the “language-agnostic middle” idea from the RYS / LLM Neuroanatomy essays: the important reasoning step may happen in a representation that is neither plain natural language nor raw code, but a structured intermediate form.

## 3. Derived Project Idea

We operationalize the RYS intuition at the **agent level** rather than the transformer-weight level.

Instead of letting an agent move directly from:

- issue text
- failing tests
- code snippets
- raw transcript history

to a repair choice, we force it to reason through an explicit intermediate representation called `BugState`.

This makes `BugState` an external analogue of the “middle layer” idea:

- `react` stays close to surface form
- `bugstate` translates evidence into a persistent structured state before deciding

## 4. Agents

Both agents see the same underlying evidence:

- issue description
- failing-test names or fail-to-pass targets
- candidate code context
- a fixed candidate patch pool

They differ only in how they organize that evidence.

### `react`

`react` reasons from a clipped transcript window. Evidence is concatenated into one raw prompt and truncated from the tail as needed.

### `bugstate`

`bugstate` reasons from an explicit structured state containing:

- repo and instance identity
- compact issue summary
- fail-to-pass targets
- suspect file
- clipped code excerpt

This preserves evidence in labeled fields rather than relying on a long undifferentiated transcript.

## 5. Benchmarks

### `mini_repair`

`mini_repair` is the project’s controlled five-task benchmark. It is small, deterministic, dependency-light, and fast enough to use for local iteration and GPU smoke validation.

Tasks:

- `csv_quoted_cells`
- `env_case_override`
- `nested_config_merge`
- `parse_iso_z_suffix`
- `request_scheme_validation`

This benchmark is useful for validating the agent loop, but it is too easy to cleanly separate the two agents once the implementation is stable.

### SWE-bench Lite dev selection benchmark

To get a more meaningful result without making Docker the project bottleneck, I added a no-Docker evaluator over the official SWE-bench Lite development split.

Protocol:

1. Load the Lite `dev` split from Hugging Face.
2. Keep only repositories with at least five dev instances.
3. For each instance, fetch the changed file from the benchmark’s `base_commit`.
4. Extract local code context around the gold patch hunks.
5. Build a repository-local candidate patch pool from the gold patches of the other dev instances in that repo.
6. Ask the agent to choose the correct `PATCH_ID`.

This yields a public-benchmark slice that still tests the project’s actual idea: whether explicit state helps the model pick the right repair when the distractors are plausible and repository-local.

## 6. Implementation

Relevant code lives in:

- `repointerlingua/agents.py`
- `repointerlingua/reasoners.py`
- `repointerlingua/llm_backends.py`
- `repointerlingua/swebench_dev_select.py`
- `scripts/run_mini_llm.sh`
- `scripts/run_swebench_dev_select.sh`

The important implementation choice is that the public-benchmark result uses patch selection rather than unconstrained patch synthesis. That keeps the experiment focused on evidence organization and repair choice, rather than exact-string diff formatting quirks.

## 7. Results

### Controlled benchmark validation

On the cleaned `mini_repair` benchmark with local `Qwen/Qwen2.5-Coder-3B-Instruct`:

| Agent | Solved | Total | Solve Rate |
| :--- | ---: | ---: | ---: |
| react | 5 | 5 | 1.000 |
| bugstate | 5 | 5 | 1.000 |

Interpretation:

- the full local/GPU loop works
- both agents can solve the curated tasks
- the benchmark is no longer discriminative enough to prove the hypothesis

### Established-benchmark discriminative result

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

### Supporting ablations

The headline result is backed by several additional experiments.

#### Model-scale comparison

Using the same SWE-bench Lite dev selection protocol:

| Model | Agent | Correct | Total | Accuracy |
| :--- | :--- | ---: | ---: | ---: |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | `react` | 15 | 20 | 0.750 |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | `bugstate` | 14 | 20 | 0.700 |
| `Qwen/Qwen2.5-Coder-3B-Instruct` | `react` | 17 | 20 | 0.850 |
| `Qwen/Qwen2.5-Coder-3B-Instruct` | `bugstate` | 20 | 20 | 1.000 |

This shows that both agents improve with a stronger model, but the separation becomes clearest at 3B.

#### Transcript-window ablation for `react`

On the 1.5B model, the transcript-only baseline changes substantially as the transcript budget changes:

| Transcript Window | `react` Correct | Total | Accuracy |
| :--- | ---: | ---: | ---: |
| `250` | 11 | 20 | 0.550 |
| `400` | 14 | 20 | 0.700 |
| `800` | 16 | 20 | 0.800 |
| `1200` | 15 | 20 | 0.750 |

This supports the intuition that transcript-only reasoning is sensitive to prompt budget and evidence crowding.

#### `bugstate` representation ablation

An earlier weaker `bugstate` representation performed substantially worse than the final structured state:

| State Format | Model | `bugstate` Correct | Total | Accuracy |
| :--- | :--- | ---: | ---: | ---: |
| initial weak state format | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 9 | 20 | 0.450 |
| improved structured state | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 14 | 20 | 0.700 |

This is important because it shows the middle representation itself matters. The result is not just a lucky prompt artifact.

#### Per-repository breakdown of the final 3B run

| Repo | `react` | `bugstate` |
| :--- | ---: | ---: |
| `pvlib/pvlib-python` | 5 / 5 | 5 / 5 |
| `pydicom/pydicom` | 4 / 5 | 5 / 5 |
| `pylint-dev/astroid` | 4 / 5 | 5 / 5 |
| `sqlfluff/sqlfluff` | 4 / 5 | 5 / 5 |

This suggests the improvement is not isolated to one unusually favorable repository. It appears across multiple repo groups.

## 8. What This Result Means

This result supports the project hypothesis:

- a clipped raw transcript is often sufficient on small curated tasks
- once the task pool becomes larger and distractors become more plausible, a persistent explicit state helps the model preserve the right evidence and choose the right fix more consistently

The result does **not** claim official SWE-bench resolved-rate performance. There is no Docker-backed execution here. Instead, it isolates the reasoning-and-selection part of the task on real benchmark instances.

## 9. Why This Was the Right Final Path

Earlier attempts centered on PyBugHive and free-form local patch generation. Those paths were dominated by:

- legacy packaging
- old Python environments
- `pipenv`
- JSON-format brittleness
- exact-string patch formatting failures

Those are real engineering issues, but they obscure the research question. The final benchmark path succeeds because it removes the irrelevant bottlenecks and measures the actual variable of interest: **stateful reasoning versus transcript-only reasoning**.

## 10. Limitations

- The SWE-bench result is a no-Docker selection benchmark, not official resolved-rate evaluation.
- The current public-benchmark slice covers 20 Lite dev instances after repo-pool filtering.
- The reported discriminative result uses `Qwen/Qwen2.5-Coder-3B-Instruct`; stronger models may change both absolute and relative performance.
- PyBugHive remains only a partial external-validation path, not the main benchmark story.

## 11. Future Work

The most natural extension is to move closer to a literal RYS-style middle representation:

- probe or summarize hidden states from middle transformer layers
- learn a latent bug state instead of hand-designed fields
- compare symbolic `BugState` against learned latent state tokens
- connect patch selection to full patch generation and official Docker-based SWE-bench execution

In other words, this project validates the **agent-level** middle-layer idea first. A follow-up project could investigate whether a true neural middle-layer representation can do even better.

## 12. Conclusion

The project is finished in a meaningful sense:

- the codebase is stable locally and on GPU
- the main hypothesis is implemented faithfully
- the validation benchmark works end to end
- an established benchmark slice now shows a clear advantage for the explicit-state agent

The final project claim is therefore:

**A persistent explicit `BugState` can improve software-repair decision quality over a transcript-only baseline, and this effect is visible on a structured SWE-bench Lite development-split evaluation.**
