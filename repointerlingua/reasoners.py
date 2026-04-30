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


def _trim_list(values: list[str], limit: int) -> list[str]:
    return values[:limit]


def _format_section(title: str, values: list[str]) -> str:
    if not values:
        return f"{title}:\n- (none)"
    body = "\n".join(f"- {value}" for value in values)
    return f"{title}:\n{body}"


def _format_bug_state(state: BugState) -> str:
    sections = [
        _format_section("Issue Facts", state.issue_facts),
        _format_section("Test Facts", state.test_facts),
        _format_section("Code Facts", state.code_facts),
        _format_section("Error Messages", state.error_messages),
        _format_section("Suspect Files", state.suspect_files),
        _format_section("Hypotheses", state.hypotheses),
        _format_section("Constraints", state.constraints),
        _format_section("Patches Considered", state.patches_considered),
    ]
    return "\n\n".join(sections)


def _truncate_patch_choices(patch_choices: list[dict], limit: int = 12) -> list[dict]:
    normalized = []
    for choice in patch_choices[:limit]:
        normalized.append(
            {
                "patch_id": choice["patch_id"],
                "source_task": choice["source_task"],
                "path": choice["path"],
                "search": _truncate_for_prompt(choice["search"], 240),
                "replace": _truncate_for_prompt(choice["replace"], 240),
            }
        )
    return normalized


def _format_patch_choices(patch_choices: list[dict]) -> str:
    lines = []
    for choice in patch_choices:
        lines.append(f"PATCH_ID: {choice['patch_id']}")
        lines.append(f"PATH: {choice['path']}")
        lines.append(f"SEARCH:")
        lines.append(choice["search"])
        lines.append("REPLACE:")
        lines.append(choice["replace"])
        lines.append("")
    return "\n".join(lines).strip()


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


def accumulate_bug_state(task: TaskSpec, state: BugState, observation: Observation) -> BugState:
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

    updated.issue_facts = _trim_list(updated.issue_facts, 12)
    updated.test_facts = _trim_list(updated.test_facts, 12)
    updated.code_facts = _trim_list(updated.code_facts, 12)
    updated.error_messages = _trim_list(updated.error_messages, 12)
    updated.suspect_files = _trim_list(updated.suspect_files, 8)
    updated.hypotheses = _trim_list(updated.hypotheses, 8)
    updated.constraints = _trim_list(updated.constraints, 8)
    updated.patches_considered = _trim_list(updated.patches_considered, 8)
    return updated


class PatternReasoner:
    name = "pattern"

    def update_bug_state(self, task: TaskSpec, state: BugState, observation: Observation) -> BugState:
        return accumulate_bug_state(task, state, observation)

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

    def select_patch_from_state(
        self,
        task: TaskSpec,
        state: BugState,
        patch_choices: list[dict],
    ) -> list[PatchOperation]:
        if _check_clues(state.combined_text(), task.bugstate_clues):
            return task.reference_patch
        return []

    def select_patch_from_transcript(self, task: TaskSpec, transcript: str, patch_choices: list[dict]) -> list[PatchOperation]:
        if _check_clues(transcript, task.react_clues):
            return task.reference_patch
        return []


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

    def _extract_choice(self, text: str, valid_ids: set[str]) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None
        for patch_id in valid_ids:
            if patch_id in normalized:
                return patch_id
        choice_match = re.search(r'"patch_id"\s*:\s*"([^"]+)"', normalized)
        if choice_match:
            patch_id = choice_match.group(1)
            if patch_id in valid_ids:
                return patch_id
        return None

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
            self.backend.generate(messages, max_tokens=384),
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
        payload = self._extract_json(self.backend.generate(messages, max_tokens=384), required_keys={"patches"})
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
        payload = self._extract_json(self.backend.generate(messages, max_tokens=384), required_keys={"patches"})
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

    def select_patch_from_state(
        self,
        task: TaskSpec,
        state: BugState,
        patch_choices: list[dict],
    ) -> list[PatchOperation]:
        preview_choices = _truncate_patch_choices(patch_choices)
        valid_ids = {choice["patch_id"] for choice in preview_choices}
        messages = [
            Message(
                role="system",
                content=(
                    "You are a software repair agent. Choose the single best candidate patch. "
                    "Return only one line in the form PATCH_ID: <id>. "
                    "If no candidate is appropriate, return PATCH_ID: NONE."
                ),
            ),
            Message(
                role="user",
                content=(
                    f"Task title: {task.title}\n\n"
                    f"BugState:\n{_format_bug_state(state)}\n\n"
                    f"Candidate patches:\n{_format_patch_choices(preview_choices)}\n\n"
                    "Pick the best patch id."
                ),
            ),
        ]
        raw = self.backend.generate(messages, max_tokens=32)
        patch_id = self._extract_choice(raw, valid_ids)
        if patch_id is None:
            return []
        selected = next(choice for choice in patch_choices if choice["patch_id"] == patch_id)
        return [
            PatchOperation(
                path=selected["path"],
                search=selected["search"],
                replace=selected["replace"],
            )
        ]

    def select_patch_from_transcript(self, task: TaskSpec, transcript: str, patch_choices: list[dict]) -> list[PatchOperation]:
        preview_choices = _truncate_patch_choices(patch_choices)
        valid_ids = {choice["patch_id"] for choice in preview_choices}
        messages = [
            Message(
                role="system",
                content=(
                    "You are a software repair agent. Choose the single best candidate patch. "
                    "Return only one line in the form PATCH_ID: <id>. "
                    "If no candidate is appropriate, return PATCH_ID: NONE."
                ),
            ),
            Message(
                role="user",
                content=(
                    f"Task title: {task.title}\n\n"
                    f"Transcript:\n{transcript}\n\n"
                    f"Candidate patches:\n{_format_patch_choices(preview_choices)}\n\n"
                    "Pick the best patch id."
                ),
            ),
        ]
        raw = self.backend.generate(messages, max_tokens=32)
        patch_id = self._extract_choice(raw, valid_ids)
        if patch_id is None:
            return []
        selected = next(choice for choice in patch_choices if choice["patch_id"] == patch_id)
        return [
            PatchOperation(
                path=selected["path"],
                search=selected["search"],
                replace=selected["replace"],
            )
        ]
