from __future__ import annotations

from pathlib import Path

from repointerlingua.schemas import PatchOperation


class PatchApplyError(RuntimeError):
    pass


def apply_patch_operation(workspace: Path, operation: PatchOperation) -> None:
    target = workspace / operation.path
    if not target.exists():
        raise PatchApplyError(f"Patch target does not exist: {target}")

    original = target.read_text(encoding="utf-8")
    if operation.search not in original:
        raise PatchApplyError(f"Search block not found in {operation.path}")

    updated = original.replace(operation.search, operation.replace, 1)
    target.write_text(updated, encoding="utf-8")


def apply_patch_set(workspace: Path, operations: list[PatchOperation]) -> None:
    for operation in operations:
        apply_patch_operation(workspace, operation)
