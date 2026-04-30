from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from datasets import load_dataset

from repointerlingua.llm_backends import Message, OpenAIBackend, TransformersBackend
from repointerlingua.reasoners import JsonPromptReasoner
from repointerlingua.utils import clamp_tail, ensure_dir, write_json, write_text


@dataclass
class SWEbenchDevSelectTask:
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    fail_to_pass: list[str]
    file_path: str
    code_excerpt: str
    patch_choices: list[dict[str, str]]
    correct_patch_id: str


@dataclass
class SWEbenchStructuredState:
    repo: str
    instance_id: str
    issue_summary: str
    fail_to_pass: list[str]
    suspect_file: str
    code_excerpt: str


def _build_backend(backend_name: str, model: str):
    if backend_name == "transformers":
        return TransformersBackend(model)
    if backend_name == "openai":
        return OpenAIBackend(model)
    raise ValueError(f"Unsupported backend: {backend_name}")


def _raw_file_url(repo: str, commit: str, relative_path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{commit}/{relative_path}"


def _fetch_cached_file(repo: str, commit: str, relative_path: str, cache_root: Path) -> str:
    cache_path = cache_root / repo.replace("/", "__") / commit / relative_path
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    url = _raw_file_url(repo, commit, relative_path)
    try:
        with urllib.request.urlopen(url) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(payload, encoding="utf-8")
    return payload


def _changed_files_from_patch(patch: str) -> list[str]:
    return re.findall(r"^diff --git a/(.*?) b/", patch, flags=re.MULTILINE)


def _changed_line_numbers(patch: str) -> list[int]:
    numbers = []
    for start, _count in re.findall(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", patch, flags=re.MULTILINE):
        numbers.append(int(start))
    return numbers


def _extract_code_excerpt(text: str, line_numbers: list[int], radius: int) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    if not line_numbers:
        selected = lines[: min(len(lines), radius * 2)]
        return "\n".join(f"{index + 1:04d}: {line}" for index, line in enumerate(selected))

    blocks: list[str] = []
    seen_ranges: list[tuple[int, int]] = []
    for line_number in line_numbers:
        start = max(1, line_number - radius)
        end = min(len(lines), line_number + radius)
        if seen_ranges and start <= seen_ranges[-1][1] + 1:
            prev_start, prev_end = seen_ranges[-1]
            seen_ranges[-1] = (prev_start, max(prev_end, end))
        else:
            seen_ranges.append((start, end))

    for start, end in seen_ranges:
        block_lines = [f"{index:04d}: {lines[index - 1]}" for index in range(start, end + 1)]
        blocks.append("\n".join(block_lines))
    return "\n\n...\n\n".join(blocks)


def _compact_problem_statement(text: str, limit: int = 2200) -> str:
    normalized = text.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:1600] + "\n...\n" + normalized[-400:]


def _compact_patch_diff(patch: str, limit: int = 1200) -> str:
    lines = []
    for line in patch.splitlines():
        if line.startswith("diff --git") or line.startswith("index "):
            continue
        if line.startswith("--- ") or line.startswith("+++ ") or line.startswith("@@ "):
            lines.append(line)
            continue
        if line.startswith("+") or line.startswith("-") or line.startswith(" "):
            lines.append(line)
    normalized = "\n".join(lines).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:900] + "\n...\n" + normalized[-200:]


def _format_patch_choices(patch_choices: list[dict[str, str]]) -> str:
    lines = []
    for choice in patch_choices:
        lines.append(f"PATCH_ID: {choice['patch_id']}")
        lines.append(f"REPO: {choice['repo']}")
        lines.append(f"FILE: {choice['file_path']}")
        lines.append("PATCH:")
        lines.append(choice["patch_preview"])
        lines.append("")
    return "\n".join(lines).strip()


def _head_clip(text: str, limit: int) -> str:
    normalized = text.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 5] + "\n..."


def _build_structured_state(
    task: SWEbenchDevSelectTask,
    *,
    issue_limit: int = 700,
    code_limit: int = 900,
    max_tests: int = 12,
) -> SWEbenchStructuredState:
    return SWEbenchStructuredState(
        repo=task.repo,
        instance_id=task.instance_id,
        issue_summary=_head_clip(task.problem_statement, issue_limit),
        fail_to_pass=task.fail_to_pass[:max_tests],
        suspect_file=task.file_path,
        code_excerpt=_head_clip(task.code_excerpt, code_limit),
    )


def _format_structured_state(state: SWEbenchStructuredState) -> str:
    sections = [
        f"Repo:\n- {state.repo}",
        f"Instance:\n- {state.instance_id}",
        f"Suspect File:\n- {state.suspect_file}",
        "Issue Summary:\n" + state.issue_summary,
        "Fail-to-Pass Tests:\n" + "\n".join(f"- {name}" for name in state.fail_to_pass),
        "Code Excerpt:\n" + state.code_excerpt,
    ]
    return "\n\n".join(sections)


def load_swebench_lite_dev_tasks(
    cache_root: Path,
    *,
    min_repo_pool_size: int = 5,
    code_context_radius: int = 40,
) -> list[SWEbenchDevSelectTask]:
    dataset = load_dataset("SWE-bench/SWE-bench_Lite")["dev"]
    repo_counts = Counter(dataset["repo"])
    filtered_rows = []
    for row in dataset:
        changed_files = _changed_files_from_patch(row["patch"])
        if len(changed_files) != 1:
            continue
        if repo_counts[row["repo"]] < min_repo_pool_size:
            continue
        filtered_rows.append(row)

    patch_choices_by_repo: dict[str, list[dict[str, str]]] = {}
    for row in filtered_rows:
        file_path = _changed_files_from_patch(row["patch"])[0]
        patch_choices_by_repo.setdefault(row["repo"], []).append(
            {
                "patch_id": row["instance_id"],
                "repo": row["repo"],
                "file_path": file_path,
                "patch_preview": _compact_patch_diff(row["patch"]),
            }
        )

    tasks: list[SWEbenchDevSelectTask] = []
    for row in filtered_rows:
        file_path = _changed_files_from_patch(row["patch"])[0]
        code_text = _fetch_cached_file(row["repo"], row["base_commit"], file_path, cache_root)
        code_excerpt = _extract_code_excerpt(code_text, _changed_line_numbers(row["patch"]), code_context_radius)
        tasks.append(
            SWEbenchDevSelectTask(
                instance_id=row["instance_id"],
                repo=row["repo"],
                base_commit=row["base_commit"],
                problem_statement=_compact_problem_statement(row["problem_statement"]),
                fail_to_pass=list(row["FAIL_TO_PASS"]),
                file_path=file_path,
                code_excerpt=code_excerpt,
                patch_choices=patch_choices_by_repo[row["repo"]],
                correct_patch_id=row["instance_id"],
            )
        )
    return tasks


def _react_prompt(task: SWEbenchDevSelectTask, transcript_window_chars: int) -> str:
    transcript = "\n\n".join(
        [
            f"[issue]\n{task.problem_statement}",
            "[fail_to_pass]\n" + "\n".join(f"- {name}" for name in task.fail_to_pass[:12]),
            f"[code:{task.file_path}]\n{task.code_excerpt}",
        ]
    )
    return clamp_tail(transcript, transcript_window_chars)


def _select_patch_from_react(
    reasoner: JsonPromptReasoner,
    task: SWEbenchDevSelectTask,
    transcript_window_chars: int,
) -> tuple[str | None, str]:
    valid_ids = {choice["patch_id"] for choice in task.patch_choices}
    transcript = _react_prompt(task, transcript_window_chars)
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
                f"Repo: {task.repo}\n"
                f"Instance: {task.instance_id}\n\n"
                f"Transcript:\n{transcript}\n\n"
                f"Candidate patches:\n{_format_patch_choices(task.patch_choices)}\n\n"
                "Pick the best patch id."
            ),
        ),
    ]
    raw = reasoner.backend.generate(messages, max_tokens=32)
    return reasoner._extract_choice(raw, valid_ids), transcript


def _select_patch_from_bugstate(
    reasoner: JsonPromptReasoner,
    task: SWEbenchDevSelectTask,
) -> tuple[str | None, SWEbenchStructuredState]:
    valid_ids = {choice["patch_id"] for choice in task.patch_choices}
    state = _build_structured_state(task)
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
                f"Repo: {task.repo}\n"
                f"Instance: {task.instance_id}\n\n"
                f"BugState:\n{_format_structured_state(state)}\n\n"
                f"Candidate patches:\n{_format_patch_choices(task.patch_choices)}\n\n"
                "Pick the best patch id."
            ),
        ),
    ]
    raw = reasoner.backend.generate(messages, max_tokens=32)
    return reasoner._extract_choice(raw, valid_ids), state


def _write_summary(results: list[dict[str, Any]], out_dir: Path) -> None:
    write_json(out_dir / "summary.json", {"results": results})
    by_agent: dict[str, dict[str, Any]] = {}
    for result in results:
        row = by_agent.setdefault(
            result["agent"],
            {"correct": 0, "total": 0},
        )
        row["total"] += 1
        row["correct"] += int(result["correct"])
    lines = ["# SWE-bench Lite Dev Patch-Selection Summary", ""]
    lines.append("| Agent | Correct | Total | Accuracy |")
    lines.append("| :--- | ---: | ---: | ---: |")
    agent_order = ["react", "bugstate"]
    for agent in agent_order:
        if agent not in by_agent:
            continue
        row = by_agent[agent]
        accuracy = row["correct"] / row["total"] if row["total"] else 0.0
        lines.append(f"| {agent} | {row['correct']} | {row['total']} | {accuracy:.3f} |")
    lines.append("")
    lines.append("## Per-instance outcomes")
    lines.append("")
    lines.append("| Instance | Repo | Agent | Correct | Chosen | Expected | Pool |")
    lines.append("| :--- | :--- | :--- | :---: | :--- | :--- | ---: |")
    result_order = sorted(
        results,
        key=lambda row: (row["repo"], row["agent"] != "react", row["instance_id"]),
    )
    for result in result_order:
        correct = "yes" if result["correct"] else "no"
        lines.append(
            f"| {result['instance_id']} | {result['repo']} | {result['agent']} | {correct} | "
            f"{result['selected_patch_id'] or 'NONE'} | {result['correct_patch_id']} | {result['pool_size']} |"
        )
    lines.append("")
    lines.append(
        "This benchmark uses the SWE-bench Lite development split with oracle patch pools grouped by repository. "
        "It measures whether the agent can choose the correct gold patch given the issue statement, fail-to-pass tests, "
        "and code context, without relying on Docker-based execution."
    )
    write_text(out_dir / "summary.md", "\n".join(lines))


def run(args: argparse.Namespace) -> None:
    output_dir = ensure_dir(Path(args.output))
    cache_root = ensure_dir(output_dir / "_cache")
    tasks = load_swebench_lite_dev_tasks(
        cache_root,
        min_repo_pool_size=args.min_repo_pool_size,
        code_context_radius=args.code_context_radius,
    )
    if args.limit:
        tasks = tasks[: args.limit]

    backend = _build_backend(args.backend, args.model)
    reasoner = JsonPromptReasoner(backend)
    results: list[dict[str, Any]] = []

    for agent in args.agents:
        for task in tasks:
            if agent == "react":
                selected_patch_id, transcript = _select_patch_from_react(reasoner, task, args.transcript_window_chars)
                prompt_size = len(transcript)
                state_payload: dict[str, Any] | None = None
            elif agent == "bugstate":
                selected_patch_id, state = _select_patch_from_bugstate(reasoner, task)
                prompt_size = len(_format_structured_state(state))
                state_payload = {
                    "repo": state.repo,
                    "instance_id": state.instance_id,
                    "issue_summary": state.issue_summary,
                    "fail_to_pass": state.fail_to_pass,
                    "suspect_file": state.suspect_file,
                    "code_excerpt": state.code_excerpt,
                }
            else:
                raise ValueError(f"Unsupported agent: {agent}")

            correct = selected_patch_id == task.correct_patch_id
            row = {
                "instance_id": task.instance_id,
                "repo": task.repo,
                "agent": agent,
                "correct": correct,
                "selected_patch_id": selected_patch_id,
                "correct_patch_id": task.correct_patch_id,
                "pool_size": len(task.patch_choices),
                "file_path": task.file_path,
                "transcript_window_chars": args.transcript_window_chars if agent == "react" else None,
                "prompt_chars": prompt_size,
                "state": state_payload,
            }
            agent_dir = ensure_dir(output_dir / agent / task.instance_id)
            write_json(agent_dir / "result.json", row)
            results.append(row)
            print(
                f"{agent} on {task.instance_id}: correct={correct} "
                f"(chosen={selected_patch_id}, expected={task.correct_patch_id})"
            )

    _write_summary(results, output_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SWE-bench Lite dev patch-selection evaluator")
    parser.add_argument("--backend", default="transformers")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--agents", nargs="+", default=["react", "bugstate"], choices=["react", "bugstate"])
    parser.add_argument("--transcript-window-chars", type=int, default=1200)
    parser.add_argument("--min-repo-pool-size", type=int, default=5)
    parser.add_argument("--code-context-radius", type=int, default=40)
    parser.add_argument("--limit", type=int)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
