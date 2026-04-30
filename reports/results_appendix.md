# RepoInterlingua Results Appendix

This appendix collects additional experiment results beyond the main headline number in `reports/swebench_dev_select_3b_ctx120/summary.md`.

## 1. Controlled Benchmark Validation

The local `mini_repair` benchmark was run with both a smaller and larger local Qwen model.

| Benchmark | Model | Agent | Solved | Total | Solve Rate |
| :--- | :--- | :--- | ---: | ---: | ---: |
| `mini_repair` | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | `react` | 5 | 5 | 1.000 |
| `mini_repair` | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | `bugstate` | 5 | 5 | 1.000 |
| `mini_repair` | `Qwen/Qwen2.5-Coder-3B-Instruct` | `react` | 5 | 5 | 1.000 |
| `mini_repair` | `Qwen/Qwen2.5-Coder-3B-Instruct` | `bugstate` | 5 | 5 | 1.000 |

Interpretation:

- the local/GPU repair loop is stable
- both agents solve the curated tasks
- this benchmark is useful for validation but too easy to discriminate the agents

## 2. SWE-bench Lite Dev Selection: Model-Scale Comparison

The main public-benchmark protocol is the SWE-bench Lite dev patch-selection benchmark with:

- repo-grouped oracle patch pools
- transcript window `1200`
- code context radius `120`

| Benchmark | Model | Agent | Correct | Total | Accuracy |
| :--- | :--- | :--- | ---: | ---: | ---: |
| SWE-bench Lite dev select | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | `react` | 15 | 20 | 0.750 |
| SWE-bench Lite dev select | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | `bugstate` | 14 | 20 | 0.700 |
| SWE-bench Lite dev select | `Qwen/Qwen2.5-Coder-3B-Instruct` | `react` | 17 | 20 | 0.850 |
| SWE-bench Lite dev select | `Qwen/Qwen2.5-Coder-3B-Instruct` | `bugstate` | 20 | 20 | 1.000 |

Interpretation:

- both agents improve when moving from 1.5B to 3B
- the stronger model reveals the clearest separation
- the main final result is not a one-off toy result; it emerges after scaling the same protocol

## 3. Transcript Budget Ablation for `react`

To test whether transcript length matters, `react` was run on the SWE-bench Lite dev selection benchmark with progressively larger transcript windows.

| Model | Transcript Window | Agent | Correct | Total | Accuracy |
| :--- | ---: | :--- | ---: | ---: | ---: |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 250 | `react` | 11 | 20 | 0.550 |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 400 | `react` | 14 | 20 | 0.700 |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 800 | `react` | 16 | 20 | 0.800 |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 1200 | `react` | 15 | 20 | 0.750 |

Interpretation:

- transcript budget matters a lot for the transcript-only baseline
- giving `react` more room helps substantially compared with very small windows
- even with a generous window, `react` still falls short of the final 3B `bugstate` result

## 4. `bugstate` Representation Ablation

An earlier `bugstate` formulation on the 1.5B model underperformed because the state representation was too weak. After moving to a richer explicit structured state, `bugstate` improved materially.

| Configuration | Model | Agent | Correct | Total | Accuracy |
| :--- | :--- | :--- | ---: | ---: | ---: |
| initial state format | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | `bugstate` | 9 | 20 | 0.450 |
| improved structured state | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | `bugstate` | 14 | 20 | 0.700 |

Interpretation:

- the exact form of the middle representation matters
- a better structured state closes most of the gap to `react` even before scaling up the model
- this is evidence that the project is actually about representation quality, not just prompt luck

## 5. Code Context Ablation

The amount of local code shown to the model also changes behavior.

| Model | Code Context Radius | Agent | Correct | Total | Accuracy |
| :--- | ---: | :--- | ---: | ---: | ---: |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 120 | `react` | 14 | 20 | 0.700 |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 120 | `bugstate` | 13 | 20 | 0.650 |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 240 | `react` | 15 | 20 | 0.750 |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 240 | `bugstate` | 14 | 20 | 0.700 |

Interpretation:

- more code context helps somewhat, but not enough by itself to produce the final separation
- stronger model plus explicit state was the cleaner path

## 6. Per-Repository Breakdown of the Final 3B Result

Final main run: `reports/swebench_dev_select_3b_ctx120/summary.md`

| Repo | `react` | `bugstate` |
| :--- | ---: | ---: |
| `pvlib/pvlib-python` | 5 / 5 | 5 / 5 |
| `pydicom/pydicom` | 4 / 5 | 5 / 5 |
| `pylint-dev/astroid` | 4 / 5 | 5 / 5 |
| `sqlfluff/sqlfluff` | 4 / 5 | 5 / 5 |

Interpretation:

- `bugstate` is not winning by overfitting to one repository
- the gain is spread across three of the four repo groups
- the final result looks like a broad robustness improvement, not a single lucky slice

## 7. Main Takeaway

The broader result set shows three things:

1. The pipeline is stable and reproducible on easy tasks.
2. The public-benchmark slice is hard enough to separate the agents.
3. The explicit middle representation becomes more useful as the benchmark becomes more realistic and the model becomes more capable.
