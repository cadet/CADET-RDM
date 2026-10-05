import pytest
from pathlib import Path
import random
import os
import subprocess

from click.testing import CliRunner

from cadetrdm.cli_integration import cli
from cadetrdm.io_utils import delete_path

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def create_repo():
    if os.path.exists("test_repo_cli"):
        delete_path("test_repo_cli")
    os.makedirs("test_repo_cli", exist_ok=True)
    os.chdir("test_repo_cli")
    result = runner.invoke(cli, ["init", ])


def modify_code(path_to_repo):
    # Add changes to the project code
    random_number = random.randint(0, 265)
    filepath = Path(path_to_repo) / f"print_random_number.py"
    with open(filepath, "w") as file:
        file.write(
            'with open("output/data.txt", "w") as handle:\n'
            f"    handle.write('{random_number}')\n"
        )


def test_01_initialize_repo():
    try:
        if os.path.exists("test_repo_cli"):
            delete_path("test_repo_cli")
        os.makedirs("test_repo_cli", exist_ok=True)

        os.chdir("test_repo_cli")
        result = runner.invoke(cli, ["init", ])
        print(result.output)
        assert result.exit_code == 0
    finally:
        os.chdir("..")


def test_02_add_remote():
    try:
        create_repo()
        result = runner.invoke(cli, ["remote", "add", "https://github.com/cadet/RDM-Testing-Template"])
        print(result.output)
        assert result.exit_code == 0
        os.chdir("output")
        result = runner.invoke(cli, ["remote", "add", "https://github.com/cadet/RDM-Testing-Template-Output"])
        print(result.output)
        os.chdir("..")
        assert result.exit_code == 0
    finally:
        os.chdir("..")


def test_02b_clone():
    root = Path.cwd()
    remote_project = root / "remote_project.git"
    remote_output = root / "remote_output.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote_project)], check=True)
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote_output)], check=True)

    try:
        create_repo()
        os.chdir("output")
        result = runner.invoke(cli, ["remote", "add", str(remote_output)])
        assert result.exit_code == 0, result.output
        subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
        os.chdir("..")
        subprocess.run(["git", "remote", "add", "origin", str(remote_project)], check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
    finally:
        os.chdir(root)

    result = runner.invoke(cli, ["clone", str(remote_project), "test_repo_cli_cloned"])
    print(result.output)
    assert result.exit_code == 0
    assert (root / "test_repo_cli_cloned" / "output" / ".git").exists()


def test_03_commit_results_with_uncommited_code_changes():
    try:
        create_repo()
        modify_code(".")

        result = runner.invoke(cli, ["run_yml", "python", "print_random_number.py",
                                     "create data"])
        print(result.output)
        assert result.exit_code != 0
    finally:
        os.chdir("..")


def test_04_commit_code():
    try:
        create_repo()
        modify_code(".")

        result = runner.invoke(cli, ["commit", "-m", "add code", "-a"])
        print(result.output)
        assert result.exit_code == 0
    finally:
        os.chdir("..")


# def test_05_commit_results():
#     result = runner.invoke(cli, ["commit", "-m", "add code", "-a"])
#     print(result.output)
#     assert result.exit_code == 0
#     result = runner.invoke(cli, ["run_yml", "python", "print_random_number.py",
#                                  "create data"])
#     print(result.output)
#     assert result.exit_code == 0
#

def test_05b_execute_command():
    try:
        create_repo()
        modify_code(".")
        result = runner.invoke(cli, ["commit", "-a", "-m", "add code"])
        print(result.output)
        assert result.exit_code == 0

        filepath = Path(".") / f"print_random_number.py"
        result = runner.invoke(cli, ["run", "command", f"python {filepath.absolute().as_posix()}",
                                     "create data"])
        print(result.output)
        assert result.exit_code == 0
    finally:
        os.chdir("..")


def test_06_print_log():
    try:
        create_repo()
        result = runner.invoke(cli, ["log"])
        print(result.output)
        assert result.exit_code == 0
    finally:
        os.chdir("..")


def test_07_lfs_add():
    try:
        create_repo()
        result = runner.invoke(cli, ["lfs", "add", "pptx"])
        print(result.output)
        assert result.exit_code == 0
    finally:
        os.chdir("..")


def test_08_data_import():
    try:
        create_repo()
        result = runner.invoke(cli,
                               [
                                   "data", "clone",
                                   "git@github.com:cadet/CADET-Core.git",
                                   "master",
                                   "imported/repo/data"
                               ])
        print(result.stdout)
        assert result.exit_code == 0
    finally:
        os.chdir("..")


# def test_09_data_verify():
#     with open()
#     result = runner.invoke(cli, ["data", "verify"])
