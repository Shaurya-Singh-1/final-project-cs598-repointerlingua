from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from repointerlingua.schemas import EpisodeResult
from repointerlingua.utils import write_json, write_text


def summarize_results(results: list[EpisodeResult]) -> dict:
    by_agent = defaultdict(lambda: {"solved": 0, "total": 0, "patched": 0})
    for result in results:
        row = by_agent[result.agent_name]
        row["total"] += 1
        row["solved"] += int(result.solved)
        row["patched"] += int(result.patch_applied)
    summary = {"agents": {}}
    for agent_name, row in by_agent.items():
        solved = row["solved"]
        total = row["total"] or 1
        summary["agents"][agent_name] = {
            **row,
            "solve_rate": round(solved / total, 3),
        }
    summary["task_results"] = [result.to_dict() for result in results]
    return summary


def write_summary(summary: dict, out_dir: Path) -> None:
    write_json(out_dir / "summary.json", summary)

    lines = []
    lines.append("# Local Result Summary")
    lines.append("")
    lines.append("| Agent | Solved | Total | Solve Rate | Patches Applied |")
    lines.append("| :--- | ---: | ---: | ---: | ---: |")
    for agent_name, row in summary["agents"].items():
        lines.append(
            f"| {agent_name} | {row['solved']} | {row['total']} | {row['solve_rate']:.3f} | {row['patched']} |"
        )
    lines.append("")
    lines.append("## Per-task outcomes")
    lines.append("")
    lines.append("| Task | Agent | Solved | Patch Applied |")
    lines.append("| :--- | :--- | :---: | :---: |")
    for row in summary["task_results"]:
        solved = "yes" if row["solved"] else "no"
        patched = "yes" if row["patch_applied"] else "no"
        lines.append(f"| {row['task_id']} | {row['agent_name']} | {solved} | {patched} |")
    lines.append("")
    lines.append(
        "This local benchmark is a system-validation benchmark: it checks that the workspace-copy, "
        "evaluation, patching, and explicit-state machinery all work before larger GPU-backed runs."
    )
    write_text(out_dir / "summary.md", "\n".join(lines))
