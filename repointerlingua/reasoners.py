from __future__ import annotations

import json
import re
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


def _truncate_for_prompt(text: str, limit: int = 1600) -> str:
    if len(text) <= limit:
        return text
    head = text[:1000]
    tail = text[-400:]
    return f"{head}\n...\n{tail}"


def _coerce_string_list(values) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        if isinstance(value, str):
            item = value.strip()
        elif isinstance(value, dict):
            parts = []
            for key in ("title", "description", "file", "path", "command", "output", "content", "note"):
                raw = value.get(key)
                if raw:
                    parts.append(str(raw).strip())
            item = " | ".join(parts)
        else:
            item = str(value).strip()
        if item:
            normalized.append(_truncate_for_prompt(item, 220))
    return normalized[:8]


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
        elif observation.kind == "patch_feedback":
            updated.error_messages.extend(_compact_lines(observation.content))

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

    def _extract_json(self, text: str, required_keys: set[str] | None = None) -> dict:
        normalized = text.strip()
        if not normalized:
            raise ValueError(f"Could not find JSON object in model output: {text}")

        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", normalized, re.DOTALL)
        candidates: list[str] = []
        if fence_match:
            candidates.append(fence_match.group(1))

        decoder = json.JSONDecoder()
        for index, char in enumerate(normalized):
            if char != "{":
                continue
            try:
                payload, end = decoder.raw_decode(normalized[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                candidate = normalized[index : index + end]
                candidates.append(candidate)

        for candidate in candidates:
            payload = json.loads(candidate)
            if required_keys and not required_keys.issubset(payload.keys()):
                continue
            return payload

        raise ValueError(f"Could not find JSON object in model output: {text}")

    def update_bug_state(self, task: TaskSpec, state: BugState, observation: Observation) -> BugState:
        observation_content = _truncate_for_prompt(observation.content, limit=1200)
        messages = [
            Message(
                role="system",
                content=(
                    "You are updating a persistent BugState for a software debugging agent. "
                    "Return JSON only. Do not use markdown fences. "
                    "Every field value must be an array of short strings, never objects. "
                    "Do not include task_id. Do not copy full code blocks. "
                    "Valid keys are issue_facts, test_facts, code_facts, "
                    "error_messages, suspect_files, hypotheses, constraints, patches_considered. "
                    'Example: {"issue_facts":["..."],"test_facts":["..."],"code_facts":["..."],'
                    '"error_messages":["..."],"suspect_files":["path.py"],"hypotheses":["..."],'
                    '"constraints":["..."],"patches_considered":["..."]}'
                ),
            ),
            Message(
                role="user",
                content=(
                    f"Task title: {task.title}\n\n"
                    f"Current state:\n{json.dumps(state.to_dict(), indent=2)}\n\n"
                    f"New observation ({observation.kind}):\n{observation_content}\n\n"
                    "Summarize only the most important facts. "
                    "Keep each list short and each item under 160 characters.\n\n"
                    "Return the updated BugState JSON."
                ),
            ),
        ]
        payload = self._extract_json(
            self.backend.generate(messages),
            required_keys={
                "issue_facts",
                "test_facts",
                "code_facts",
                "error_messages",
                "suspect_files",
                "hypotheses",
                "constraints",
                "patches_considered",
            },
        )
        payload.pop("task_id", None)
        return BugState(
            task_id=task.task_id,
            issue_facts=_coerce_string_list(payload.get("issue_facts")),
            test_facts=_coerce_string_list(payload.get("test_facts")),
            code_facts=_coerce_string_list(payload.get("code_facts")),
            error_messages=_coerce_string_list(payload.get("error_messages")),
            suspect_files=_coerce_string_list(payload.get("suspect_files")),
            hypotheses=_coerce_string_list(payload.get("hypotheses")),
            constraints=_coerce_string_list(payload.get("constraints")),
            patches_considered=_coerce_string_list(payload.get("patches_considered")),
        )

    def propose_patch_from_state(
        self,
        task: TaskSpec,
        state: BugState,
        code_observations: list[Observation] | None = None,
    ) -> list[PatchOperation]:
        code_payload = []
        for observation in code_observations or []:
            code_payload.append({"path": observation.path, "content": _truncate_for_prompt(observation.content, 2200)})
        messages = [
            Message(
                role="system",
                content=(
                    "You are a software repair agent. Return JSON only with keys rationale and patches. "
                    "Each patch must have path, search, and replace. "
                    "Use only file paths that appear in Candidate files exactly. "
                    "The search text must be copied verbatim from a Candidate file. "
                    "Use the smallest unique exact search block you can find. "
                    "If unsure, return an empty patches list. Never invent placeholder paths."
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
        payload = self._extract_json(self.backend.generate(messages), required_keys={"patches"})
        patches = []
        for patch in payload.get("patches", []):
            if not isinstance(patch, dict):
                continue
            if not {"path", "search", "replace"}.issubset(patch.keys()):
                continue
            patches.append(
                PatchOperation(
                    path=patch["path"],
                    search=patch["search"],
                    replace=patch["replace"],
                )
            )
        return patches

    def propose_patch_from_transcript(self, task: TaskSpec, transcript: str) -> list[PatchOperation]:
        messages = [
            Message(
                role="system",
                content=(
                    "You are a software repair agent with limited context. Return JSON only with keys rationale and patches. "
                    "Each patch must have path, search, and replace. "
                    "Use only file paths that appear in the transcript exactly. "
                    "The search text must be copied verbatim from the transcript. "
                    "Use the smallest unique exact search block you can find. "
                    "If unsure, return an empty patches list. Never invent placeholder paths."
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
        payload = self._extract_json(self.backend.generate(messages), required_keys={"patches"})
        patches = []
        for patch in payload.get("patches", []):
            if not isinstance(patch, dict):
                continue
            if not {"path", "search", "replace"}.issubset(patch.keys()):
                continue
            patches.append(
                PatchOperation(
                    path=patch["path"],
                    search=patch["search"],
                    replace=patch["replace"],
                )
            )
        return patches
