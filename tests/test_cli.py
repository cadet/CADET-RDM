import pytest
from pathlib import Path
import random
import os

from click.testing import CliRunner

from cadetrdm.cli_integration import cli
from cadetrdm.io_utils import delete_path

runner = CliRunner()
if os.path.exists("test_repo_cli"):
    delete_path("test_repo_cli")

os.makedirs("test_repo_cli")
os.chdir("test_repo_cli")


def modify_code(path_to_repo):
    # Add changes to the project code
    random_number = random.randint(0, 265)
    filepath = Path(path_to_repo) / f"print_random_number.py"
    with open(filepath, "w") as file:
        file.write(
            f"print({random_number})\n"
            'with open("output/data.txt", "w") as handle:\n'
            f"    handle.write({random_number})\n"
        )


def test_01_initialize_repo():
    result = runner.invoke(cli, ["init", ])
    print(result.output)
    assert result.exit_code == 0


def test_02_add_remote():
    result = runner.invoke(cli, ["remote", "add", "https://jugit.fz-juelich.de/r.jaepel/API_test_project"])
    print(result.output)
    assert result.exit_code == 0
    os.chdir("output")
    result = runner.invoke(cli, ["remote", "add", "https://jugit.fz-juelich.de/r.jaepel/API_test_project_output"])
    print(result.output)
    os.chdir("..")
    assert result.exit_code == 0


@pytest.mark.server_api
def test_02b_clone():
    os.chdir("..")
    if os.path.exists("test_repo_cli_cloned"):
        delete_path("test_repo_cli_cloned")
    result = runner.invoke(cli, ["clone", "test_repo_cli", "test_repo_cli_cloned"])
    print(result.output)
    os.chdir("test_repo_cli")
    assert result.exit_code == 0


def test_03_commit_results_with_uncommited_code_changes():
    modify_code(".")

    result = runner.invoke(cli, ["run", "python", "print_random_number.py",
                                 "create data"])
    print(result.output)
    assert result.exit_code != 0


def test_04_commit_code():
    modify_code(".")

    result = runner.invoke(cli, ["commit", "-m", "add code", "-a"])
    print(result.output)
    assert result.exit_code == 0


# def test_05_commit_results():
#     result = runner.invoke(cli, ["commit", "-m", "add code", "-a"])
#     print(result.output)
#     assert result.exit_code == 0
#     result = runner.invoke(cli, ["run", "python", "print_random_number.py",
#                                  "create data"])
#     print(result.output)
#     assert result.exit_code == 0
#
#
# def test_05b_execute_command():
#     result = runner.invoke(cli, ["commit", "-m", "add code", "-a"])
#     print(result.output)
#     assert result.exit_code == 0
#     result = runner.invoke(cli, ["run", "command", "python", "print_random_number.py",
#                                  "create data"])
#     print(result.output)
#     assert result.exit_code == 0


def test_06_print_log():
    result = runner.invoke(cli, ["log"])
    print(result.output)
    assert result.exit_code == 0


def test_07_lfs_add():
    result = runner.invoke(cli, ["lfs", "add", "pptx"])
    print(result.output)
    assert result.exit_code == 0


def test_08_data_import():
    result = runner.invoke(cli,
                           ["data", "import", "https://github.com/ronald-jaepel/workshop_demo_output",
                            "2023-12-19_10-43-15_output_from_master_86541bc", "imported/repo/data"])
    print(result.output)
    assert result.exit_code == 0

# def test_09_data_verify():
#     with open()
#     result = runner.invoke(cli, ["data", "verify"])
