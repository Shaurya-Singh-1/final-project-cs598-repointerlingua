from __future__ import annotations

import argparse
from pathlib import Path

from repointerlingua.agents import build_agent
from repointerlingua.benchmark import load_mini_repair_tasks, load_pybughive_tasks, prepare_pybughive_manifest
from repointerlingua.llm_backends import OpenAIBackend, TransformersBackend
from repointerlingua.reasoners import JsonPromptReasoner, PatternReasoner
from repointerlingua.reporting import summarize_results, write_summary
from repointerlingua.schemas import EpisodeResult
from repointerlingua.training import export_sft_data, train_lora
from repointerlingua.utils import ensure_dir, repo_root, write_json


def _build_reasoner(args):
    if args.reasoner == "pattern":
        return PatternReasoner()
    if args.reasoner != "llm":
        raise ValueError(f"Unknown reasoner: {args.reasoner}")
    if args.backend == "openai":
        backend = OpenAIBackend(args.model)
    elif args.backend == "transformers":
        backend = TransformersBackend(args.model)
    else:
        raise ValueError(f"Unknown backend: {args.backend}")
    return JsonPromptReasoner(backend)


def _load_tasks(args):
    if args.benchmark == "mini_repair":
        tasks = load_mini_repair_tasks()
    elif args.benchmark == "pybughive":
        if not args.manifest:
            raise ValueError("--manifest is required for the pybughive benchmark.")
        tasks = load_pybughive_tasks(Path(args.manifest))
    else:
        raise ValueError(f"Unsupported benchmark: {args.benchmark}")

    if getattr(args, "task_id", None):
        wanted = set(args.task_id)
        tasks = [task for task in tasks if task.task_id in wanted]

    if getattr(args, "limit", None):
        tasks = tasks[: args.limit]

    return tasks


def _make_failure_result(args, agent_name: str, task, exc: Exception) -> EpisodeResult:
    return EpisodeResult(
        benchmark=args.benchmark,
        task_id=task.task_id,
        agent_name=agent_name,
        reasoner_name=args.reasoner,
        solved=False,
        patch_applied=False,
        tests_passed_before=False,
        tests_passed_after=False,
        transcript_chars=0,
        observations=[],
        patches=[],
        state_history=[],
        workspace="",
        notes=[f"execution error: {exc}"],
    )


def _persist_failure_result(run_dir: Path, result: EpisodeResult) -> None:
    ensure_dir(run_dir)
    write_json(run_dir / "episode.json", result.to_dict())


def cmd_list_tasks(_args):
    tasks = load_mini_repair_tasks()
    for task in tasks:
        print(f"{task.task_id}: {task.title}")


def cmd_eval(args):
    tasks = _load_tasks(args)
    reasoner = _build_reasoner(args)
    agent = build_agent(
        args.agent,
        reasoner,
        transcript_window_chars=args.transcript_window_chars,
        max_patch_attempts=args.max_patch_attempts,
    )
    output_dir = ensure_dir(Path(args.output))
    results = []
    for task in tasks:
        run_dir = output_dir / args.agent / task.task_id
        try:
            results.append(agent.run(task, run_dir))
        except Exception as exc:
            results.append(_make_failure_result(args, args.agent, task, exc))
            _persist_failure_result(run_dir, results[-1])
            print(f"{args.agent} on {task.task_id}: error={exc}")
        print(f"{args.agent} on {task.task_id}: solved={results[-1].solved}")
    summary = summarize_results(results)
    write_summary(summary, output_dir / args.agent)


def cmd_compare(args):
    tasks = _load_tasks(args)
    output_dir = ensure_dir(Path(args.output))
    results = []

    for agent_name in args.agents:
        reasoner = _build_reasoner(args)
        agent = build_agent(
            agent_name,
            reasoner,
            transcript_window_chars=args.transcript_window_chars,
            max_patch_attempts=args.max_patch_attempts,
        )
        for task in tasks:
            run_dir = output_dir / agent_name / task.task_id
            try:
                result = agent.run(task, run_dir)
            except Exception as exc:
                result = _make_failure_result(args, agent_name, task, exc)
                _persist_failure_result(run_dir, result)
                print(f"{agent_name} on {task.task_id}: error={exc}")
            results.append(result)
            print(f"{agent_name} on {task.task_id}: solved={result.solved}")

    summary = summarize_results(results)
    write_summary(summary, output_dir)


def cmd_prepare_pybughive(args):
    count = prepare_pybughive_manifest(Path(args.dataset), Path(args.output))
    print(f"Wrote {count} PyBugHive rows to {args.output}")


def cmd_export_sft(args):
    counts = export_sft_data(Path(args.runs), Path(args.output))
    print(f"Exported state updates: {counts['state_updates']}")
    print(f"Exported patch generation examples: {counts['patch_generation']}")


def cmd_train_lora(args):
    train_lora(Path(args.train_file), args.model, Path(args.output_dir), epochs=args.epochs)
    print(f"Finished LoRA training into {args.output_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RepoInterlingua research project CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-tasks")

    eval_parser = subparsers.add_parser("eval")
    eval_parser.add_argument("--benchmark", default="mini_repair")
    eval_parser.add_argument("--agent", required=True, choices=["react", "bugstate"])
    eval_parser.add_argument("--reasoner", default="pattern", choices=["pattern", "llm"])
    eval_parser.add_argument("--backend", default="transformers")
    eval_parser.add_argument("--model", default="")
    eval_parser.add_argument("--output", required=True)
    eval_parser.add_argument("--transcript-window-chars", type=int, default=1200)
    eval_parser.add_argument("--max-patch-attempts", type=int, default=2)
    eval_parser.add_argument("--manifest")
    eval_parser.add_argument("--task-id", action="append")
    eval_parser.add_argument("--limit", type=int)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--benchmark", default="mini_repair")
    compare_parser.add_argument("--agents", nargs="+", required=True, choices=["react", "bugstate"])
    compare_parser.add_argument("--reasoner", default="pattern", choices=["pattern", "llm"])
    compare_parser.add_argument("--backend", default="transformers")
    compare_parser.add_argument("--model", default="")
    compare_parser.add_argument("--output", required=True)
    compare_parser.add_argument("--transcript-window-chars", type=int, default=1200)
    compare_parser.add_argument("--max-patch-attempts", type=int, default=2)
    compare_parser.add_argument("--manifest")
    compare_parser.add_argument("--task-id", action="append")
    compare_parser.add_argument("--limit", type=int)

    manifest_parser = subparsers.add_parser("prepare-pybughive")
    manifest_parser.add_argument("--dataset", required=True)
    manifest_parser.add_argument("--output", required=True)

    export_parser = subparsers.add_parser("export-sft")
    export_parser.add_argument("--runs", required=True)
    export_parser.add_argument("--output", required=True)

    train_parser = subparsers.add_parser("train-lora")
    train_parser.add_argument("--train-file", required=True)
    train_parser.add_argument("--model", required=True)
    train_parser.add_argument("--output-dir", required=True)
    train_parser.add_argument("--epochs", type=int, default=1)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list-tasks":
        cmd_list_tasks(args)
    elif args.command == "eval":
        cmd_eval(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "prepare-pybughive":
        cmd_prepare_pybughive(args)
    elif args.command == "export-sft":
        cmd_export_sft(args)
    elif args.command == "train-lora":
        cmd_train_lora(args)
    else:
        parser.error(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    main()
