"""Regression tests pinning that reading results does not mutate git state.

Loading archived results must not move either repository. These tests snapshot the
observable git state of both repositories, perform a read, and assert the snapshot is
unchanged.
"""

from pathlib import Path

import pytest

from cadetrdm import Case, Options, ProjectRepo, initialize_repo
from cadetrdm.io_utils import delete_path


def git_state(repo):
    """Snapshot the observable git state of a repository.

    Covers everything a read operation must leave alone: the checked out commit and
    branch, the set of local branches, and whether the working tree is dirty.
    """
    return {
        "commit": repo.current_commit_hash,
        "branch": str(repo.active_branch),
        "branches": sorted(head.name for head in repo._git_repo.heads),
        "is_dirty": repo._git_repo.is_dirty(untracked_files=True),
    }


@pytest.fixture
def repo_with_results(tmp_path):
    """A project repo holding one recorded result, left on the result branch.

    Leaving the output repo on the result branch rather than on main is what makes the
    mutation visible: a read that checks out main would change the active branch.
    """
    path_to_repo = tmp_path / "project"
    initialize_repo(path_to_repo, "results")

    repo = ProjectRepo(path_to_repo)
    with repo.track_results(results_commit_message="Add result"):
        (repo.output_path / "result.csv").write_text("1,2,3\n")

    assert str(repo.output_repo.active_branch) != repo.output_repo.main_branch

    return repo


@pytest.fixture
def case_with_results(tmp_path):
    path_to_repo = tmp_path / "project"
    initialize_repo(path_to_repo, "results")

    repo = ProjectRepo(path_to_repo)
    options = Options({"case": "read-only-load"})
    options.branch_prefix = "read-only-load"

    with repo.track_results(results_commit_message="Add result", options=options):
        (repo.output_path / "result.csv").write_text("1,2,3\n")

    case = Case(project_repo=repo, options=options, name="read-only-load")
    cache_folder = repo.cache_folder_for_branch(str(repo.output_repo.active_branch))
    delete_path(cache_folder)

    return case


def test_reading_output_log_leaves_output_repo_untouched(repo_with_results):
    output_repo = repo_with_results.output_repo
    state_before = git_state(output_repo)

    output_repo.output_log

    assert git_state(output_repo) == state_before


def test_reading_output_log_preserves_uncommitted_changes(repo_with_results):
    output_repo = repo_with_results.output_repo
    scratch_file = Path(output_repo.path) / "uncommitted.txt"
    scratch_file.write_text("work in progress\n")

    output_repo.output_log

    assert scratch_file.exists(), "reading the log discarded uncommitted work"
    assert scratch_file.read_text() == "work in progress\n"


def test_output_log_read_without_checkout_lists_the_result_branch(repo_with_results):
    output_repo = repo_with_results.output_repo
    result_branch = str(output_repo.active_branch)

    entries = output_repo.output_log.entries

    assert result_branch in entries
    assert entries[result_branch].project_repo_commit_hash == repo_with_results.current_commit_hash


def test_matching_without_an_environment_does_not_read_run_history(repo_with_results):
    """Without requirements to match, recorded environments must not be read.

    run_history is only populated on the main branch, so on a result branch the
    conda_environment.yml a LogEntry would load is not in the working tree. Reading it
    used to work only because reading the log checked out main first.
    """
    output_repo = repo_with_results.output_repo
    assert not (Path(output_repo.path) / "run_history").exists()

    entry = output_repo.output_log.entries[str(output_repo.active_branch)]

    assert entry.fulfils_environment(None) is True


def test_output_log_is_empty_when_no_results_are_recorded(tmp_path):
    path_to_repo = tmp_path / "project"
    initialize_repo(path_to_repo, "results")

    repo = ProjectRepo(path_to_repo)

    assert repo.output_repo.output_log.n_entries == 0


def test_copy_data_to_cache_uses_remote_ref_without_creating_local_branch(repo_with_results):
    output_repo = repo_with_results.output_repo
    result_branch = str(output_repo.active_branch)
    result_commit = output_repo.current_commit_hash
    cache_folder = repo_with_results.cache_folder_for_branch(result_branch)

    delete_path(cache_folder)
    output_repo.checkout(output_repo.main_branch)
    output_repo._git_repo.git.update_ref(
        f"refs/remotes/origin/{result_branch}",
        result_commit,
    )
    output_repo._git_repo.delete_head(result_branch, force=True)

    state_before = git_state(output_repo)
    assert result_branch not in state_before["branches"]

    cache_path = repo_with_results.copy_data_to_cache(result_branch)

    assert (cache_path / "result.csv").read_text() == "1,2,3\n"
    assert git_state(output_repo) == state_before
    assert result_branch not in [head.name for head in output_repo._git_repo.heads]


def test_case_load_does_not_update_project_repo(case_with_results, monkeypatch):
    project_repo = case_with_results.project_repo
    project_state_before = git_state(project_repo)
    output_state_before = git_state(project_repo.output_repo)

    def fail_update():
        raise AssertionError("Case.load() updated the project repository")

    def fail_fetch():
        raise AssertionError("Case.load() fetched output repository refs by default")

    monkeypatch.setattr(project_repo, "update", fail_update)
    monkeypatch.setattr(project_repo.output_repo, "fetch", fail_fetch)

    results_path = case_with_results.load()

    assert (results_path / "result.csv").read_text() == "1,2,3\n"
    assert git_state(project_repo) == project_state_before
    assert git_state(project_repo.output_repo) == output_state_before


def test_case_load_can_fetch_output_refs_explicitly(case_with_results, monkeypatch):
    project_repo = case_with_results.project_repo
    fetched = False

    def fail_update():
        raise AssertionError("Case.load() updated the project repository")

    def fetch_output_refs():
        nonlocal fetched
        fetched = True

    monkeypatch.setattr(project_repo, "update", fail_update)
    monkeypatch.setattr(project_repo.output_repo, "fetch", fetch_output_refs)

    results_path = case_with_results.load(fetch=True)

    assert fetched is True
    assert (results_path / "result.csv").read_text() == "1,2,3\n"
