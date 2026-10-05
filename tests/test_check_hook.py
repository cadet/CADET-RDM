import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from cadetrdm import initialize_repo
from cadetrdm.cli_integration import cli

OUTPUT_REMOTE = "git@github.com:foobar/rdm_project_output.git"
OUTPUT_REMOTE_HTTP = "https://github.com/foobar/rdm_project_output"
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def git(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def project_with_new_output_remote(tmp_path):
    """Project whose output remote was added with plain git, so the links are stale."""
    project = tmp_path / "project"
    initialize_repo(project)
    git(["remote", "add", "origin", OUTPUT_REMOTE], project / "output")
    assert OUTPUT_REMOTE_HTTP not in (project / "README.md").read_text(encoding="utf-8")
    return project


def test_check_no_commit_project_only(project_with_new_output_remote, monkeypatch):
    project = project_with_new_output_remote
    output = project / "output"
    project_head = git(["rev-parse", "HEAD"], project)
    output_head = git(["rev-parse", "HEAD"], output)
    output_branch = git(["branch", "--show-current"], output)

    monkeypatch.chdir(project)
    result = CliRunner().invoke(cli, ["check", "--no-commit", "--project-only"])
    assert result.exit_code == 0, result.output

    assert git(["rev-parse", "HEAD"], project) == project_head
    staged = git(["diff", "--cached", "--name-only"], project).split()
    assert sorted(staged) == [".cadet-rdm-data.json", "README.md"]
    assert OUTPUT_REMOTE_HTTP in (project / "README.md").read_text(encoding="utf-8")
    metadata = json.loads((project / ".cadet-rdm-data.json").read_text(encoding="utf-8"))
    assert metadata["output_remotes"]["output_remotes"] == {"origin": OUTPUT_REMOTE}

    assert git(["rev-parse", "HEAD"], output) == output_head
    assert git(["branch", "--show-current"], output) == output_branch
    assert git(["status", "--porcelain"], output) == ""


@pytest.mark.skipif(sys.platform == "win32", reason="shell script hook")
def test_check_as_git_pre_commit_hook(project_with_new_output_remote):
    project = project_with_new_output_remote
    hook = project / ".git" / "hooks" / "pre-commit"
    hook.write_text(
        "#!/bin/sh\n"
        f"PYTHONPATH={shlex.quote(str(REPO_ROOT))} exec {shlex.quote(sys.executable)} "
        "-c 'from cadetrdm.cli_integration import cli; cli()' "
        "check --no-commit --project-only --warn-only\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)

    (project / "analysis.py").write_text("print('analysis')\n", encoding="utf-8")
    git(["add", "analysis.py"], project)
    git(["commit", "-m", "Add analysis"], project)

    committed_readme = git(["show", "HEAD:README.md"], project)
    assert OUTPUT_REMOTE_HTTP in committed_readme
    committed_files = git(["show", "--name-only", "--format=", "HEAD"], project).split()
    assert sorted(committed_files) == [".cadet-rdm-data.json", "README.md", "analysis.py"]
    assert git(["status", "--porcelain"], project) == ""


def test_check_warn_only_does_not_fail(tmp_path, monkeypatch):
    not_rdm = tmp_path / "not_rdm"
    not_rdm.mkdir()
    git(["init"], not_rdm)
    monkeypatch.chdir(not_rdm)

    result = CliRunner().invoke(cli, ["check", "--no-commit", "--project-only"])
    assert result.exit_code != 0

    result = CliRunner().invoke(cli, ["check", "--no-commit", "--project-only", "--warn-only"])
    assert result.exit_code == 0, result.output
    assert "Warning: rdm check failed" in result.output
