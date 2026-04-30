from __future__ import annotations

import json
from pathlib import Path

from repointerlingua.schemas import PatchOperation, TaskSpec
from repointerlingua.utils import ensure_dir, read_json, repo_root, write_jsonl, write_text


def load_mini_repair_tasks() -> list[TaskSpec]:
    tasks_root = repo_root() / "benchmarks" / "mini_repair" / "tasks"
    tasks = []
    for task_file in sorted(tasks_root.glob("*/task.json")):
        task_dir = task_file.parent
        payload = read_json(task_file)
        tasks.append(
            TaskSpec(
                benchmark="mini_repair",
                task_id=payload["task_id"],
                title=payload["title"],
                issue_path=task_dir / payload["issue_file"],
                repo_path=task_dir / payload["repo_dir"],
                test_commands=payload["test_commands"],
                candidate_files=payload["candidate_files"],
                reference_patch=[PatchOperation(**patch) for patch in payload["reference_patch"]],
                react_clues=payload.get("react_clues", []),
                bugstate_clues=payload.get("bugstate_clues", []),
                tags=payload.get("tags", []),
                metadata=payload.get("metadata", {}),
            )
        )
    return tasks


def load_pybughive_manifest(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_pybughive_tasks(manifest_path: Path) -> list[TaskSpec]:
    rows = load_pybughive_manifest(manifest_path)
    issues_root = ensure_dir(repo_root() / "reports" / "generated_pybughive_issues")
    tasks = []
    for row in rows:
        issue_text = [
            f"Project: {row['project']}",
            f"Issue: {row['issue_id']}",
            f"Title: {row['title']}",
            f"Labels: {row.get('labels', '')}",
        ]
        issue_file = issues_root / f"{row['project']}-{row['issue_id']}.md"
        write_text(issue_file, "\n".join(issue_text) + "\n")
        test_steps = [step for step in (row.get("test_steps") or "").splitlines() if step.strip()]
        tasks.append(
            TaskSpec(
                benchmark="pybughive",
                task_id=f"{row['project']}-{row['issue_id']}",
                title=row["title"],
                issue_path=issue_file,
                repo_path=Path("__pybughive_remote__"),
                test_commands=test_steps,
                candidate_files=row.get("candidate_files", []),
                reference_patch=[],
                react_clues=[],
                bugstate_clues=[],
                tags=["pybughive", row["project"]],
                metadata={
                    "materializer": "git_checkout",
                    "clone_url": f"https://github.com/{row['username']}/{row['project']}.git",
                    "buggy_commit": row["buggy_commit"],
                    "fixed_commit": row.get("fixed_commit"),
                    "changed_tests": row.get("changed_tests", []),
                    "install_commands": [step for step in (row.get("install_steps") or "").splitlines() if step.strip()],
                    "test_steps_full": [step for step in (row.get("test_steps_full") or "").splitlines() if step.strip()],
                },
            )
        )
    return tasks


def prepare_pybughive_manifest(dataset_path: Path, output_path: Path) -> int:
    dataset = read_json(dataset_path)
    rows = []
    for project in dataset:
        username = project["username"]
        repository = project["repository"]
        for issue in project["issues"]:
            commit = issue["commits"][0]
            rows.append(
                {
                    "benchmark": "pybughive",
                    "project": repository,
                    "username": username,
                    "issue_id": issue["id"],
                    "title": issue["title"],
                    "labels": issue.get("labels", ""),
                    "created_at": issue.get("created_at"),
                    "closed_at": issue.get("closed_at"),
                    "buggy_commit": commit["parents"],
                    "fixed_commit": commit["hash"],
                    "candidate_files": [item["filename"] for item in commit["stat"].get("files", [])],
                    "changed_tests": [item["filename"] for item in commit["stat"].get("tests", [])],
                    "reference_patch": [item.get("patch", "") for item in commit["stat"].get("files", [])],
                    "install_steps": issue.get("installSteps") or project.get("installSteps"),
                    "test_steps": issue.get("testSteps", ""),
                    "test_steps_full": issue.get("testStepsFull", ""),
                }
            )
    write_jsonl(output_path, rows)
    return len(rows)
