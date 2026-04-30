# RepoInterlingua Presentation Brief

Create an editable slide deck for a technical project presentation. The tone should be confident, research-oriented, and clear to an audience of technically literate students or researchers. Avoid hype. Emphasize the research question, the benchmark design, the final result, and the precise caveat that this is not official Docker-based SWE-bench resolved-rate evaluation.

Use this exact slide structure:

## Slide 1: Title

Title:
- RepoInterlingua: Explicit Bug State as an Agent-Level Middle Layer

Subtitle:
- Testing an RYS-inspired idea for software repair agents

Presenter note:
- This project asks whether a software debugging agent does better when it reasons through an explicit persistent middle representation instead of a clipped transcript.

## Slide 2: What Is RYS?

Main points:
- RYS comes from the LLM Neuroanatomy / “language-agnostic middle” framing.
- The core claim is that transformer models may have three rough stages:
- early encoding of surface form
- middle abstract reasoning
- late decoding back to tokens

Short explanation:
- The key idea is that the middle part may be less tied to literal language and more tied to meaning.
- That suggests a general design principle: reasoning may improve when a system is forced through a more abstract intermediate representation.

Presenter note:
- Do not dwell on mechanistic details. The point is the design intuition, not reproducing the original interpretability experiments.

## Slide 3: Results of RYS on Its Own

Main points:
- RYS itself is a model-level intervention, not a software debugging system.
- In the referenced RYS / Neuroanatomy work, repeating a block of middle layers was reported to improve model performance without standard fine-tuning.
- The interpretation is that middle layers are especially important for reasoning.

Important framing:
- Our project does not attempt to replicate those internal-layer interventions directly.
- Instead, it borrows the idea of a “middle layer” and reinterprets it at the agent level.

## Slide 4: Derived Idea for This Project

Main points:
- Question: can we build an agent-level analogue of the RYS “middle”?
- Baseline agent: `react`, which reasons from a clipped transcript.
- Proposed agent: `bugstate`, which reasons through an explicit persistent `BugState`.

Explain `BugState` simply:
- issue summary
- fail-to-pass tests
- suspect file
- code excerpt
- structured bug evidence

Presenter note:
- Say clearly: `BugState` is not a neural hidden state. It is an explicit external reasoning state inspired by the same abstraction principle.

## Slide 5: Experiment Setup / Pipeline

Main points:
- Step 1: validate the pipeline on a small controlled benchmark called `mini_repair`.
- Step 2: move to a public benchmark slice based on SWE-bench Lite dev.
- Both agents use the same model and same evidence budget.
- The comparison isolates the effect of explicit state versus raw transcript.

Describe the final benchmark honestly:
- We used real SWE-bench Lite dev instances.
- We filtered to repositories with at least 5 dev instances so we could build same-repo candidate patch pools.
- The task was oracle patch selection, not official Docker-based patch execution.

Technical details to include:
- Model: `Qwen/Qwen2.5-Coder-3B-Instruct`
- Controlled validation benchmark: `mini_repair`
- Main discriminative benchmark: SWE-bench Lite dev selection benchmark

## Slide 6: Our Results / Solution

Main result:
- `mini_repair`: both agents solved `5/5`
- SWE-bench Lite dev selection:
- `react`: `17/20`
- `bugstate`: `20/20`

Interpretation:
- The easy benchmark validates that the system works end to end.
- The harder public benchmark slice finally separates the agents.
- The explicit persistent state improves repair choice quality over the transcript-only baseline.

Callout:
- This is the core success of the project.

## Slide 7: Future Plan

Title:
- Going Deeper Into Neural Middle Layers

Main points:
- Current project: explicit symbolic middle layer (`BugState`)
- Next step 1: learn better structured state updates
- Next step 2: compare symbolic state to latent state tokens or embeddings
- Next step 3: probe actual middle transformer representations during debugging tasks
- Next step 4: connect this to official Docker-based SWE-bench execution

Presenter note:
- Emphasize that this project validates the agent-level version first, which creates a platform for deeper neural-middle-layer work later.

## Slide 8: Conclusion

Main points:
- RYS suggests that abstract middle representations matter.
- We translated that idea into an agent architecture for software repair.
- On a controlled SWE-bench Lite dev slice, explicit `BugState` outperformed a transcript-only baseline.
- Final takeaway: a persistent middle representation can improve software debugging decisions.

Closing line:
- The project does not prove the full internal neuroanatomy story, but it does show that the middle-layer design principle is useful in practice for software agents.

## Visual guidance

Use a clean academic style, not a marketing style.

Suggested visuals:
- Slide 2: simple 3-block pipeline diagram: encode -> middle reasoning -> decode
- Slide 4: side-by-side comparison: `react` transcript vs `bugstate` structured state
- Slide 5: pipeline diagram from issue/tests/code -> state -> patch choice
- Slide 6: bold comparison table with `17/20` vs `20/20`
- Slide 7: roadmap arrow from symbolic middle -> learned middle -> neural middle

## Accuracy constraints

Do not claim:
- official SWE-bench resolved-rate
- Docker-based evaluation
- leaderboard comparability

Do say:
- SWE-bench Lite dev slice
- no-Docker oracle patch-selection benchmark
- same model, same budget, different agent architecture
