from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PatchOperation:
    path: str
    search: str
    replace: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Observation:
    kind: str
    content: str
    path: str | None = None
    command: str | None = None
    success: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BugState:
    task_id: str
    issue_facts: list[str] = field(default_factory=list)
    test_facts: list[str] = field(default_factory=list)
    code_facts: list[str] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)
    suspect_files: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    patches_considered: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def combined_text(self) -> str:
        parts = []
        for values in (
            self.issue_facts,
            self.test_facts,
            self.code_facts,
            self.error_messages,
            self.hypotheses,
            self.constraints,
            self.patches_considered,
        ):
            parts.extend(values)
        return "\n".join(parts)


@dataclass
class TaskSpec:
    benchmark: str
    task_id: str
    title: str
    issue_path: Path
    repo_path: Path
    test_commands: list[str]
    candidate_files: list[str]
    reference_patch: list[PatchOperation]
    react_clues: list[str] = field(default_factory=list)
    bugstate_clues: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["issue_path"] = str(self.issue_path)
        payload["repo_path"] = str(self.repo_path)
        payload["reference_patch"] = [patch.to_dict() for patch in self.reference_patch]
        return payload


@dataclass
class EpisodeResult:
    benchmark: str
    task_id: str
    agent_name: str
    reasoner_name: str
    solved: bool
    patch_applied: bool
    tests_passed_before: bool
    tests_passed_after: bool
    transcript_chars: int
    observations: list[Observation] = field(default_factory=list)
    patches: list[PatchOperation] = field(default_factory=list)
    state_history: list[dict[str, Any]] = field(default_factory=list)
    workspace: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "reasoner_name": self.reasoner_name,
            "solved": self.solved,
            "patch_applied": self.patch_applied,
            "tests_passed_before": self.tests_passed_before,
            "tests_passed_after": self.tests_passed_after,
            "transcript_chars": self.transcript_chars,
            "observations": [observation.to_dict() for observation in self.observations],
            "patches": [patch.to_dict() for patch in self.patches],
            "state_history": self.state_history,
            "workspace": self.workspace,
            "notes": self.notes,
        }
