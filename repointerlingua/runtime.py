from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from repointerlingua.patching import apply_patch_set
from repointerlingua.schemas import Observation, TaskSpec
from repointerlingua.utils import ensure_dir, read_text


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def to_observation(self) -> Observation:
        body = []
        body.append(f"$ {self.command}")
        if self.stdout.strip():
            body.append(self.stdout.strip())
        if self.stderr.strip():
            body.append(self.stderr.strip())
        body.append(f"[returncode={self.returncode}]")
        return Observation(
            kind="test_output",
            content="\n".join(body),
            command=self.command,
            success=self.ok,
        )


class WorkspaceSession:
    def __init__(self, task: TaskSpec, run_root: Path):
        self.task = task
        self.run_root = ensure_dir(run_root).resolve()
        self.workspace = self.run_root / "workspace"

    def materialize(self) -> Path:
        if self.workspace.exists():
            shutil.rmtree(self.workspace)
        if self.task.metadata.get("materializer") == "git_checkout":
            self._materialize_git_checkout()
        else:
            shutil.copytree(self.task.repo_path, self.workspace)
        return self.workspace

    def _materialize_git_checkout(self) -> None:
        clone_url = self.task.metadata["clone_url"]
        buggy_commit = self.task.metadata["buggy_commit"]
        fixed_commit = self.task.metadata.get("fixed_commit")
        changed_tests = self.task.metadata.get("changed_tests", [])
        install_commands = self.task.metadata.get("install_commands", [])

        clone = subprocess.run(
            ["git", "clone", clone_url, str(self.workspace)],
            cwd=self.run_root,
            text=True,
            capture_output=True,
        )
        if clone.returncode != 0:
            raise RuntimeError(f"git clone failed: {clone.stderr or clone.stdout}")

        if fixed_commit and changed_tests:
            fixed_checkout = subprocess.run(
                ["git", "checkout", "-q", fixed_commit, "--force"],
                cwd=self.workspace,
                text=True,
                capture_output=True,
            )
            if fixed_checkout.returncode != 0:
                raise RuntimeError(f"git checkout fixed commit failed: {fixed_checkout.stderr or fixed_checkout.stdout}")

            test_cache = self.run_root / "patched_tests"
            ensure_dir(test_cache)
            for relative_path in changed_tests:
                source = self.workspace / relative_path
                if source.exists():
                    destination = test_cache / relative_path
                    ensure_dir(destination.parent)
                    shutil.copy2(source, destination)

        buggy_checkout = subprocess.run(
            ["git", "checkout", "-q", buggy_commit, "--force"],
            cwd=self.workspace,
            text=True,
            capture_output=True,
        )
        if buggy_checkout.returncode != 0:
            raise RuntimeError(f"git checkout buggy commit failed: {buggy_checkout.stderr or buggy_checkout.stdout}")

        if fixed_commit and changed_tests:
            test_cache = self.run_root / "patched_tests"
            for relative_path in changed_tests:
                cached = test_cache / relative_path
                if cached.exists():
                    destination = self.workspace / relative_path
                    ensure_dir(destination.parent)
                    shutil.copy2(cached, destination)

        install_logs = []
        for command in install_commands:
            command = self._normalize_install_command(command)
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace,
                text=True,
                capture_output=True,
            )
            install_logs.append(f"$ {command}\n{result.stdout}\n{result.stderr}\n[returncode={result.returncode}]")
            if result.returncode != 0:
                (self.run_root / "install.log").write_text("\n\n".join(install_logs), encoding="utf-8")
                raise RuntimeError(f"install command failed: {command}")
            if '-m pipenv --python' in command:
                pip_bootstrap = f'"{sys.executable}" -m pipenv run python -m pip install "pip<24"'
                bootstrap_result = subprocess.run(
                    pip_bootstrap,
                    shell=True,
                    cwd=self.workspace,
                    text=True,
                    capture_output=True,
                )
                install_logs.append(
                    f"$ {pip_bootstrap}\n{bootstrap_result.stdout}\n{bootstrap_result.stderr}\n[returncode={bootstrap_result.returncode}]"
                )
                if bootstrap_result.returncode != 0:
                    (self.run_root / "install.log").write_text("\n\n".join(install_logs), encoding="utf-8")
                    raise RuntimeError(f"install command failed: {pip_bootstrap}")
        if install_logs:
            (self.run_root / "install.log").write_text("\n\n".join(install_logs), encoding="utf-8")

    def _normalize_install_command(self, command: str) -> str:
        pipenv_runner = f'"{sys.executable}" -m pipenv'

        match = re.search(r"\bpipenv\s+--python\s+([0-9.]+)", command)
        if match:
            version = match.group(1)
            interpreter = self._resolve_python_interpreter(version)
            if interpreter is not None:
                return re.sub(
                    r"\bpipenv\s+--python\s+[0-9.]+",
                    f'{pipenv_runner} --python "{interpreter}"',
                    command,
                    count=1,
                )
            return re.sub(r"\bpipenv\b", pipenv_runner, command)

        match = re.search(r"\bpipenv\s+install\s+-r\s+(\S+)", command)
        if match:
            req_file = match.group(1)
            return f"{pipenv_runner} run python -m pip install -r {req_file}"

        match = re.search(r"\bpipenv\s+install\b(.*)", command)
        if match:
            args = match.group(1).strip()
            if args:
                return f"{pipenv_runner} run python -m pip install {args}"
            return f"{pipenv_runner} install"

        return re.sub(r"\bpipenv\b", pipenv_runner, command)

    def _resolve_python_interpreter(self, version: str) -> str | None:
        env_key = f"REPOINTERLINGUA_PYTHON_{version.replace('.', '_')}"
        if os.getenv(env_key):
            return os.environ[env_key]

        uv_binary = shutil.which("uv")
        if uv_binary:
            find_result = subprocess.run(
                [uv_binary, "python", "find", version],
                cwd=self.run_root,
                text=True,
                capture_output=True,
            )
            if find_result.returncode == 0 and find_result.stdout.strip():
                return find_result.stdout.strip()

        resolved = shutil.which(f"python{version}")
        if resolved:
            return str(Path(resolved).resolve())

        if not uv_binary:
            return None

        install_result = subprocess.run(
            [uv_binary, "python", "install", version],
            cwd=self.run_root,
            text=True,
            capture_output=True,
        )
        if install_result.returncode != 0:
            return None

        retry = subprocess.run(
            [uv_binary, "python", "find", version],
            cwd=self.run_root,
            text=True,
            capture_output=True,
        )
        if retry.returncode == 0 and retry.stdout.strip():
            return retry.stdout.strip()
        return None

    def run_command(self, command: str) -> CommandResult:
        command = self._normalize_install_command(command)
        completed = subprocess.run(
            command,
            shell=True,
            cwd=self.workspace,
            text=True,
            capture_output=True,
        )
        return CommandResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def run_tests(self) -> CommandResult:
        outputs = []
        overall = 0
        for command in self.task.test_commands:
            result = self.run_command(command)
            outputs.append(result)
            if result.returncode != 0:
                overall = result.returncode
                break
        stdout = "\n\n".join(result.stdout for result in outputs if result.stdout)
        stderr = "\n\n".join(result.stderr for result in outputs if result.stderr)
        return CommandResult(
            command=" && ".join(self.task.test_commands),
            returncode=overall,
            stdout=stdout,
            stderr=stderr,
        )

    def read_issue(self) -> Observation:
        return Observation(kind="issue", content=read_text(self.task.issue_path), path=str(self.task.issue_path))

    def read_candidate_files(self) -> list[Observation]:
        observations = []
        for relative_path in self.task.candidate_files:
            full_path = self.workspace / relative_path
            if not full_path.exists():
                observations.append(
                    Observation(
                        kind="code",
                        content=f"[missing file] {relative_path}",
                        path=relative_path,
                    )
                )
                continue
            observations.append(
                Observation(
                    kind="code",
                    content=read_text(full_path),
                    path=relative_path,
                )
            )
        return observations

    def apply_patches(self, operations: list) -> None:
        apply_patch_set(self.workspace, operations)
