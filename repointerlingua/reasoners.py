from __future__ import annotations

import json
from typing import Iterable

from repointerlingua.llm_backends import BackendProtocol, Message
from repointerlingua.schemas import BugState, Observation, PatchOperation, TaskSpec


def _compact_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:10]


def _extract_error_lines(text: str) -> list[str]:
    interesting = []
    for line in text.splitlines():
        stripped = line.strip()
        if any(token in stripped for token in ("AssertionError", "ValueError", "KeyError", "FAIL:", "ERROR:", "Traceback")):
            interesting.append(stripped)
    return interesting[:10]


def _collect_text(values: Iterable[str]) -> str:
    return "\n".join(value.lower() for value in values if value)


def _check_clues(text: str, clues: list[str]) -> bool:
    lower = text.lower()
    for clue in clues:
        if ":" not in clue:
            if clue.lower() not in lower:
                return False
            continue
        prefix, needle = clue.split(":", 1)
        needle = needle.lower()
        if prefix.endswith("_contains") and needle not in lower:
            return False
    return True


class PatternReasoner:
    name = "pattern"

    def update_bug_state(self, task: TaskSpec, state: BugState, observation: Observation) -> BugState:
        updated = BugState(**state.to_dict())
        if observation.kind == "issue":
            updated.issue_facts.extend(_compact_lines(observation.content))
            updated.constraints.extend(task.metadata.get("constraints", []))
        elif observation.kind == "test_output":
            updated.test_facts.extend(_compact_lines(observation.content))
            updated.error_messages.extend(_extract_error_lines(observation.content))
        elif observation.kind == "code":
            if observation.path and observation.path not in updated.suspect_files:
                updated.suspect_files.append(observation.path)
            updated.code_facts.extend(_compact_lines(observation.content))

        # Keep the state concise and persistent.
        updated.issue_facts = updated.issue_facts[:12]
        updated.test_facts = updated.test_facts[:12]
        updated.code_facts = updated.code_facts[:12]
        updated.error_messages = updated.error_messages[:12]
        updated.suspect_files = updated.suspect_files[:8]
        return updated

    def propose_patch_from_state(
        self,
        task: TaskSpec,
        state: BugState,
        code_observations: list[Observation] | None = None,
    ) -> list[PatchOperation]:
        evidence = _collect_text(
            state.issue_facts
            + state.test_facts
            + state.code_facts
            + state.error_messages
            + state.constraints
        )
        if _check_clues(evidence, task.bugstate_clues):
            return task.reference_patch
        return []

    def propose_patch_from_transcript(self, task: TaskSpec, transcript: str) -> list[PatchOperation]:
        if _check_clues(transcript, task.react_clues):
            return task.reference_patch
        return []

    def make_plan(self, transcript: str) -> str:
        lines = [line.strip() for line in transcript.splitlines() if line.strip()]
        selected = []
        for line in lines:
            if len(selected) >= 5:
                break
            if any(token in line for token in ("Issue", "ValueError", "KeyError", "AssertionError", "FAIL:", "ERROR:")):
                selected.append(line)
        return "\n".join(selected[:5])


class JsonPromptReasoner:
    name = "llm"

    def __init__(self, backend: BackendProtocol):
        self.backend = backend

    def _extract_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"Could not find JSON object in model output: {text}")
        return json.loads(text[start : end + 1])

    def update_bug_state(self, task: TaskSpec, state: BugState, observation: Observation) -> BugState:
        messages = [
            Message(
                role="system",
                content=(
                    "You are updating a persistent BugState for a software debugging agent. "
                    "Return JSON only with keys issue_facts, test_facts, code_facts, "
                    "error_messages, suspect_files, hypotheses, constraints, patches_considered."
                ),
            ),
            Message(
                role="user",
                content=(
                    f"Task title: {task.title}\n\n"
                    f"Current state:\n{json.dumps(state.to_dict(), indent=2)}\n\n"
                    f"New observation ({observation.kind}):\n{observation.content}\n\n"
                    "Return the updated BugState JSON."
                ),
            ),
        ]
        payload = self._extract_json(self.backend.generate(messages))
        return BugState(task_id=task.task_id, **payload)

    def propose_patch_from_state(
        self,
        task: TaskSpec,
        state: BugState,
        code_observations: list[Observation] | None = None,
    ) -> list[PatchOperation]:
        code_payload = []
        for observation in code_observations or []:
            code_payload.append({"path": observation.path, "content": observation.content})
        messages = [
            Message(
                role="system",
                content=(
                    "You are a software repair agent. Return JSON only with keys rationale and patches. "
                    "Each patch must have path, search, and replace."
                ),
            ),
            Message(
                role="user",
                content=(
                    f"Task title: {task.title}\n\n"
                    f"BugState:\n{json.dumps(state.to_dict(), indent=2)}\n\n"
                    f"Candidate files:\n{json.dumps(code_payload, indent=2)}\n\n"
                    "Return the smallest patch set that fixes the bug."
                ),
            ),
        ]
        payload = self._extract_json(self.backend.generate(messages))
        return [PatchOperation(**patch) for patch in payload.get("patches", [])]

    def propose_patch_from_transcript(self, task: TaskSpec, transcript: str) -> list[PatchOperation]:
        messages = [
            Message(
                role="system",
                content=(
                    "You are a software repair agent with limited context. Return JSON only with keys rationale and patches. "
                    "Each patch must have path, search, and replace."
                ),
            ),
            Message(
                role="user",
                content=(
                    f"Task title: {task.title}\n\n"
                    f"Transcript:\n{transcript}\n\n"
                    "Return the smallest patch set that fixes the bug."
                ),
            ),
        ]
        payload = self._extract_json(self.backend.generate(messages))
        return [PatchOperation(**patch) for patch in payload.get("patches", [])]
