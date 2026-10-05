import csv
from pathlib import Path

import pytest

from cadetrdm import ProjectRepo, initialize_repo
from cadetrdm.repositories import OutputRepo

COMMIT_HASH = "3910c84e0b5a4c1d9f8e7a6b5c4d3e2f1a0b9c8d"


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize(
    "output_branch, expected",
    [
        ("main_3910c84_output_2023-10-25-00-17-23-12", "main"),
        ("2023-10-25_00-17-23_output_from_master_3910c84", "master"),
        ("2023-10-25_00-17-23_results_from_feature_x_3910c84", "feature_x"),
        ("2024-05-02_09-30-00_main_3910c84", "main"),
        ("2024-05-02_09-30-00_fix_header_bug_3910c84", "fix_header_bug"),
        ("my_prefix_2024-05-02_09-30-00_dev_3910c84", "dev"),
        ("2026-01-09_10-00-00_main_3910c84_a1b2c3", "main"),
        ("output_from_master_3910c84_2023-10-25_00-17-23", "master"),
        ("2024-05-02_09-30-00_main_abcdef0", ""),
    ],
)
def test_project_branch_from_output_branch(output_branch, expected):
    assert OutputRepo._project_branch_from_output_branch(output_branch, COMMIT_HASH) == expected


def test_project_branch_from_output_branch_without_hash():
    output_branch = "2024-05-02_09-30-00_main_3910c84"
    assert OutputRepo._project_branch_from_output_branch(output_branch, "") == ""


def test_add_branch_name_to_log():
    initialize_repo(Path("migration_repo"))
    output_repo = ProjectRepo(Path("migration_repo")).output_repo

    header = [
        "output_repo_commit_message", "output_repo_branch", "output_repo_commit_hash",
        "project_repo_commit_hash", "project_repo_folder_name", "project_repo_remotes",
        "python_sys_args", "tags", "options_hash",
    ]
    rows = [
        ["run 1", "2023-10-25_00-17-23_output_from_master_3910c84", "a" * 40, COMMIT_HASH,
         "migration_repo", "[]", "[]", "", "hash1"],
        ["run 2", "2024-05-02_09-30-00_fix_header_bug_1234567", "b" * 40, "1234567" + "0" * 33,
         "migration_repo", "[]", "[]", "", "hash2"],
    ]
    log_path = output_repo.path / "log.tsv"
    with open(log_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(header)
        writer.writerows(rows)

    output_repo._add_branch_name_to_log()

    with open(log_path, encoding="utf-8") as handle:
        migrated = list(csv.DictReader(handle, delimiter="\t"))

    assert list(migrated[0].keys())[3] == "project_repo_branch"
    assert [row["project_repo_branch"] for row in migrated] == ["master", "fix_header_bug"]
