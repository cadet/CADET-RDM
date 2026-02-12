# tests/test_cli.py

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Mapping, Sequence

import pytest
from click.testing import CliRunner, Result

from cadetrdm.cli_integration import cli
from cadetrdm import ProjectRepo

runner = CliRunner()


def git(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command and assert success."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "git failed:\n"
            f"args={list(args)}\n"
            f"cwd={cwd}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}\n"
        )
    return result


def rdm(
    args: Sequence[str],
    cwd: Path,
    *,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
) -> Result:
    """Run the rdm CLI command via Click runner."""
    old_cwd = Path.cwd()
    try:
        os.chdir(cwd)
        return runner.invoke(cli, list(args), env=env, input=input_text)
    finally:
        os.chdir(old_cwd)


def ensure_output_origin(output_repo: Path, remote_output: Path) -> None:
    """
    Ensure output_repo has an 'origin' remote pointing to remote_output.

    Works whether origin already exists or not.
    """
    result = rdm(["remote", "list"], output_repo)
    assert result.exit_code == 0, result.output

    remote_url = str(remote_output.resolve())

    if "origin" in (result.output or ""):
        result = rdm(
            ["remote", "set-url", "origin", remote_url],
            output_repo,
        )
    else:
        result = rdm(["remote", "add", remote_url], output_repo)

    assert result.exit_code == 0, result.output


def test_two_machines_output_branch_collision(tmp_path: Path) -> None:
    """
    Simulate two machines pushing results to the same output remote.

    This test forces the same timestamp to maximize the probability of collisions.
    """
    with runner.isolated_filesystem():
        root = Path.cwd()

        # 1) Create local bare remotes (simulate server)
        remote_project = root / "remote_project.git"
        remote_output = root / "remote_output.git"
        git(["init", "--bare", str(remote_project)], root)
        git(["init", "--bare", str(remote_output)], root)

        assert (remote_project / "HEAD").exists()
        assert (remote_output / "HEAD").exists()

        # 2) Create seed repo with rdm init, commit everything, push main
        seed = root / "seed"
        result = rdm(["init", str(seed)], root)
        assert result.exit_code == 0, result.output

        git(["config", "user.email", "seed@example.org"], seed)
        git(["config", "user.name", "seed"], seed)

        (seed / "README.md").write_text("seed\n", encoding="utf-8")

        git(["add", "-A"], seed)
        git(["commit", "-m", "initial CADET RDM commit"], seed)

        git(["branch", "-M", "main"], seed)
        git(["remote", "add", "origin", str(remote_project.resolve())], seed)
        git(["push", "-u", "origin", "main"], seed)

        # Ensure bare remote HEAD points to main so clones check out main.
        git(["symbolic-ref", "HEAD", "refs/heads/main"], remote_project)

        # Configure output remote for the seed output repo.
        seed_output = seed / "output"
        assert (seed_output / ".git").exists()
        ensure_output_origin(seed_output, remote_output)

        git(["symbolic-ref", "HEAD", "refs/heads/main"], remote_output)
        git(["checkout", "-B", "main"], seed_output)
        git(["push", "-u", "origin", "main"], seed_output)

        # 3) Two "computers" clone the project
        machine_a = root / "machine_a"
        machine_b = root / "machine_b"
        git(["clone", str(remote_project.resolve()), str(machine_a)], root)
        git(["clone", str(remote_project.resolve()), str(machine_b)], root)

        git(["config", "user.email", "a@example.org"], machine_a)
        git(["config", "user.name", "machine-a"], machine_a)
        git(["config", "user.email", "b@example.org"], machine_b)
        git(["config", "user.name", "machine-b"], machine_b)

        # Ensure output repos exist in both clones.
        if not (machine_a / "output").exists():
            result = rdm(["init"], machine_a, input_text="Y\n")
            assert result.exit_code == 0, result.output

        if not (machine_b / "output").exists():
            result = rdm(["init"], machine_b, input_text="Y\n")
            assert result.exit_code == 0, result.output

        output_a = machine_a / "output"
        output_b = machine_b / "output"
        assert (output_a / ".git").exists()
        assert (output_b / ".git").exists()

        ensure_output_origin(output_a, remote_output)
        ensure_output_origin(output_b, remote_output)

        result = rdm(["check"], machine_a)
        assert result.exit_code == 0, result.output
        result = rdm(["check"], machine_b)
        assert result.exit_code == 0, result.output

        # 4) Force identical timestamp so both runs target the same output branch.
        env_fixed = dict(os.environ)
        env_fixed["CADET_RDM_FIXED_TIMESTAMP"] = "20260212_120000"

        result = rdm(
            [
                "run",
                "command",
                (
                    "python -c "
                    "\"from pathlib import Path; "
                    "Path('output/A.txt').write_text('A\\n', encoding='utf-8')\""
                ),
                "run A",
            ],
            machine_a,
            env=env_fixed,
        )
        assert result.exit_code == 0, result.output
        result = rdm(["push"], machine_a, env=env_fixed)
        assert result.exit_code == 0, result.output

        result = rdm(
            [
                "run",
                "command",
                (
                    "python -c "
                    "\"from pathlib import Path; "
                    "Path('output/B.txt').write_text('B\\n', encoding='utf-8')\""
                ),
                "run B",
            ],
            machine_b,
            env=env_fixed,
        )
        assert result.exit_code == 0, result.output

        result = rdm(["push"], machine_b, env=env_fixed)

        assert result.exit_code == 0, (
            "Push did not succeed with the following output:\n"
            f"{result.output}"
        )

        lower_output = (result.output or "").lower()
        assert (
            "rejected" in lower_output
            or "non-fast-forward" in lower_output
            or "fetch first" in lower_output
            or result.exception is not None
        ), result.output

def test_push_with_uncommitted_changes(tmp_path: Path) -> None:
    """
    If the output repo has local uncommitted changes, rdm push must not discard them
    while updating/pushing output main.

    This specifically guards against reset --hard in the user's active output checkout.
    """
    with runner.isolated_filesystem():
        root = Path.cwd()

        # 1) Create local bare remotes
        remote_project = root / "remote_project.git"
        remote_output = root / "remote_output.git"
        git(["init", "--bare", str(remote_project)], root)
        git(["init", "--bare", str(remote_output)], root)

        # 2) Seed repo, commit, push main
        seed = root / "seed"
        result = rdm(["init", str(seed)], root)
        assert result.exit_code == 0, result.output

        git(["config", "user.email", "seed@example.org"], seed)
        git(["config", "user.name", "seed"], seed)

        (seed / "README.md").write_text("seed\n", encoding="utf-8")
        git(["add", "-A"], seed)
        git(["commit", "-m", "initial CADET RDM commit"], seed)

        git(["branch", "-M", "main"], seed)
        git(["remote", "add", "origin", str(remote_project.resolve())], seed)
        git(["push", "-u", "origin", "main"], seed)
        git(["symbolic-ref", "HEAD", "refs/heads/main"], remote_project)

        # 3) Configure output remote for seed output repo and ensure output/main exists
        seed_output = seed / "output"
        assert (seed_output / ".git").exists()
        ensure_output_origin(seed_output, remote_output)

        # Add a tracked file in output repo main so we can modify it later
        git(["checkout", "-B", "main"], seed_output)
        tracked_file = seed_output / "OUT_README.md"
        tracked_file.write_text("output main base\n", encoding="utf-8")
        git(["add", "-A"], seed_output)
        git(["commit", "-m", "add tracked file to output main"], seed_output)

        git(["symbolic-ref", "HEAD", "refs/heads/main"], remote_output)
        git(["push", "-u", "origin", "main"], seed_output)

        # 4) Clone one machine
        machine = root / "machine"
        git(["clone", str(remote_project.resolve()), str(machine)], root)
        git(["config", "user.email", "m@example.org"], machine)
        git(["config", "user.name", "machine"], machine)

        # Ensure output repo exists
        if not (machine / "output").exists():
            result = rdm(["init"], machine, input_text="Y\n")
            assert result.exit_code == 0, result.output

        output_repo = machine / "output"
        ensure_output_origin(output_repo, remote_output)

        # Ensure OUT_README.md exists locally as a tracked file on output/main
        git(["checkout", "-B", "main"], output_repo)
        local_file = output_repo / "OUT_README.md"
        local_file.write_text("output main local base\n", encoding="utf-8")
        git(["add", "OUT_README.md"], output_repo)
        git(["commit", "-m", "add OUT_README locally"], output_repo)

        # 5) Create a run branch by running something (fixed timestamp for stability)
        env_fixed = dict(os.environ)
        env_fixed["CADET_RDM_FIXED_TIMESTAMP"] = "20260212_120000"

        result = rdm(
            [
                "run",
                "command",
                (
                    "python -c "
                    "\"from pathlib import Path; "
                    "Path('output/runfile.txt').write_text('run\\n', encoding='utf-8')\""
                ),
                "create run output",
            ],
            machine,
            env=env_fixed,
        )
        assert result.exit_code == 0, result.output

        # 6) Introduce a local uncommitted change in that tracked file
        assert local_file.exists()
        local_file.write_text("LOCAL UNCOMMITTED CHANGE", encoding="utf-8")

        # Confirm it's dirty (tracked modification)
        dirty = git(["status", "--porcelain"], output_repo).stdout
        assert "OUT_README.md" in dirty

        # 7) Push. This must not discard the uncommitted change above.
        result = rdm(["push"], machine, env=env_fixed)
        assert result.exit_code == 0, result.output

        # If reset --hard was used in the active checkout, this would revert.
        assert local_file.read_text(encoding="utf-8") == "LOCAL UNCOMMITTED CHANGE"
