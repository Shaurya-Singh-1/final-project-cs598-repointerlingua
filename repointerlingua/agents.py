from __future__ import annotations

from pathlib import Path

from repointerlingua.patching import PatchApplyError
from repointerlingua.reasoners import JsonPromptReasoner, PatternReasoner
from repointerlingua.runtime import WorkspaceSession
from repointerlingua.schemas import BugState, EpisodeResult, Observation, PatchOperation, TaskSpec
from repointerlingua.utils import clamp_tail, ensure_dir, write_json


class BaseAgent:
    def __init__(
        self,
        name: str,
        reasoner,
        transcript_window_chars: int = 900,
        max_patch_attempts: int = 2,
        repair_mode: str = "synthesize",
    ):
        self.name = name
        self.reasoner = reasoner
        self.transcript_window_chars = transcript_window_chars
        self.max_patch_attempts = max_patch_attempts
        self.repair_mode = repair_mode

    def _persist_result(self, run_dir: Path, result: EpisodeResult) -> None:
        ensure_dir(run_dir)
        write_json(run_dir / "episode.json", result.to_dict())

    def _filter_patch_set(
        self,
        patch_set: list[PatchOperation],
        code_observations: list[Observation],
        notes: list[str],
    ) -> list[PatchOperation]:
        allowed_paths = {
            observation.path
            for observation in code_observations
            if observation.path and not observation.content.startswith("[missing file]")
        }
        filtered = [patch for patch in patch_set if patch.path in allowed_paths]
        dropped = [patch.path for patch in patch_set if patch.path not in allowed_paths]
        if dropped:
            notes.append(f"Dropped patch proposals outside candidate files: {', '.join(dropped[:5])}")
        return filtered


class ReactiveTranscriptAgent(BaseAgent):
    def __init__(
        self,
        reasoner,
        transcript_window_chars: int = 900,
        max_patch_attempts: int = 2,
        repair_mode: str = "synthesize",
    ):
        super().__init__(
            "react",
            reasoner,
            transcript_window_chars=transcript_window_chars,
            max_patch_attempts=max_patch_attempts,
            repair_mode=repair_mode,
        )

    def run(self, task: TaskSpec, run_dir: Path) -> EpisodeResult:
        session = WorkspaceSession(task, run_dir)
        session.materialize()
        observations: list[Observation] = []
        transcript = []
        code_observations = []

        issue_observation = session.read_issue()
        observations.append(issue_observation)
        transcript.append(f"[issue]\n{issue_observation.content}")

        initial = session.run_tests()
        initial_observation = initial.to_observation()
        observations.append(initial_observation)
        transcript.append(f"[tests-before]\n{initial_observation.content}")

        for code_observation in session.read_candidate_files():
            observations.append(code_observation)
            code_observations.append(code_observation)
            transcript.append(f"[code:{code_observation.path}]\n{code_observation.content}")

        patch_applied = False
        final_result = initial
        notes = []
        patch_set = []

        for attempt in range(1, self.max_patch_attempts + 1):
            clipped = clamp_tail("\n\n".join(transcript), self.transcript_window_chars)
            if self.repair_mode == "select":
                patch_set = self.reasoner.select_patch_from_transcript(
                    task,
                    clipped,
                    task.metadata.get("patch_choices", []),
                )
            else:
                patch_set = self.reasoner.propose_patch_from_transcript(task, clipped)
            patch_set = self._filter_patch_set(patch_set, code_observations, notes)

            if not patch_set:
                if attempt == 1:
                    notes.append("No patch proposed from transcript window.")
                else:
                    notes.append(f"No valid patch proposed from transcript window on attempt {attempt}.")
                break

            try:
                session.apply_patches(patch_set)
            except PatchApplyError as exc:
                feedback = Observation(kind="patch_feedback", content=str(exc))
                observations.append(feedback)
                transcript.append(f"[patch-error:{attempt}]\n{feedback.content}")
                notes.append(f"Patch application failed on transcript attempt {attempt}: {exc}")
                if attempt == self.max_patch_attempts:
                    break
                continue

            patch_applied = True
            final_result = session.run_tests()
            observations.append(final_result.to_observation())
            notes.append(f"Patch proposed from transcript window on attempt {attempt}.")
            break

        result = EpisodeResult(
            benchmark=task.benchmark,
            task_id=task.task_id,
            agent_name=self.name,
            reasoner_name=self.reasoner.name,
            solved=patch_applied and final_result.ok,
            patch_applied=patch_applied,
            tests_passed_before=initial.ok,
            tests_passed_after=final_result.ok,
            transcript_chars=len(clipped),
            observations=observations,
            patches=patch_set,
            state_history=[],
            workspace=str(session.workspace),
            notes=notes,
        )
        self._persist_result(run_dir, result)
        return result


class BugStateAgent(BaseAgent):
    def __init__(
        self,
        reasoner,
        transcript_window_chars: int = 900,
        max_patch_attempts: int = 2,
        repair_mode: str = "synthesize",
    ):
        super().__init__(
            "bugstate",
            reasoner,
            transcript_window_chars=transcript_window_chars,
            max_patch_attempts=max_patch_attempts,
            repair_mode=repair_mode,
        )

    def run(self, task: TaskSpec, run_dir: Path) -> EpisodeResult:
        session = WorkspaceSession(task, run_dir)
        session.materialize()
        observations: list[Observation] = []
        state_history: list[dict] = []
        state = BugState(task_id=task.task_id)
        code_observations = []

        issue_observation = session.read_issue()
        observations.append(issue_observation)
        state = self.reasoner.update_bug_state(task, state, issue_observation)
        state_history.append({"step": "issue", "state": state.to_dict()})

        initial = session.run_tests()
        initial_observation = initial.to_observation()
        observations.append(initial_observation)
        state = self.reasoner.update_bug_state(task, state, initial_observation)
        state_history.append({"step": "tests-before", "state": state.to_dict()})

        for code_observation in session.read_candidate_files():
            observations.append(code_observation)
            code_observations.append(code_observation)
            state = self.reasoner.update_bug_state(task, state, code_observation)
            state_history.append({"step": f"read:{code_observation.path}", "state": state.to_dict()})

        patch_applied = False
        final_result = initial
        notes = []
        patch_set = []

        for attempt in range(1, self.max_patch_attempts + 1):
            if self.repair_mode == "select":
                patch_set = self.reasoner.select_patch_from_state(
                    task,
                    state,
                    task.metadata.get("patch_choices", []),
                )
            else:
                patch_set = self.reasoner.propose_patch_from_state(task, state, code_observations)
            patch_set = self._filter_patch_set(patch_set, code_observations, notes)

            if not patch_set:
                if attempt == 1:
                    notes.append("No patch proposed from BugState.")
                else:
                    notes.append(f"No valid patch proposed from BugState on attempt {attempt}.")
                break

            try:
                session.apply_patches(patch_set)
            except PatchApplyError as exc:
                feedback = Observation(kind="patch_feedback", content=str(exc))
                observations.append(feedback)
                state = self.reasoner.update_bug_state(task, state, feedback)
                state_history.append({"step": f"patch-feedback:{attempt}", "state": state.to_dict()})
                notes.append(f"Patch application failed on BugState attempt {attempt}: {exc}")
                if attempt == self.max_patch_attempts:
                    break
                continue

            patch_applied = True
            final_result = session.run_tests()
            observations.append(final_result.to_observation())
            notes.append(f"Patch proposed from persistent BugState on attempt {attempt}.")
            break

        result = EpisodeResult(
            benchmark=task.benchmark,
            task_id=task.task_id,
            agent_name=self.name,
            reasoner_name=self.reasoner.name,
            solved=patch_applied and final_result.ok,
            patch_applied=patch_applied,
            tests_passed_before=initial.ok,
            tests_passed_after=final_result.ok,
            transcript_chars=0,
            observations=observations,
            patches=patch_set,
            state_history=state_history,
            workspace=str(session.workspace),
            notes=notes,
        )
        self._persist_result(run_dir, result)
        return result


def build_agent(
    agent_name: str,
    reasoner,
    transcript_window_chars: int = 900,
    max_patch_attempts: int = 2,
    repair_mode: str = "synthesize",
):
    if agent_name == "react":
        return ReactiveTranscriptAgent(
            reasoner,
            transcript_window_chars=transcript_window_chars,
            max_patch_attempts=max_patch_attempts,
            repair_mode=repair_mode,
        )
    if agent_name == "bugstate":
        return BugStateAgent(
            reasoner,
            transcript_window_chars=transcript_window_chars,
            max_patch_attempts=max_patch_attempts,
            repair_mode=repair_mode,
        )
    raise ValueError(f"Unknown agent: {agent_name}")
