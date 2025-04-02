import os
import random
from pathlib import Path

import git
import numpy as np
import pytest

from cadetrdm import initialize_repo, ProjectRepo, Options
from cadetrdm.initialize_repo import init_lfs
from cadetrdm.io_utils import delete_path
from cadetrdm.repositories import OutputRepo, BaseRepo
from cadetrdm.web_utils import ssh_url_to_http_url
from cadetrdm.wrapper import tracks_results


@pytest.fixture(scope="module")
def path_to_repo():
    # a "fixture" serves up shared, ready variables to test functions that should use the fixture as a kwarg
    return Path("test_repo")


def modify_code(path_to_repo):
    # Add changes to the project code
    random_number = random.randint(0, 265)
    filepath = path_to_repo / f"print_random_number.py"
    with open(filepath, "w") as file:
        file.write(f"print({random_number})\n")


def count_commit_number(repo):
    commit_log = repo._git.log("--oneline").split("\n")
    current_commit_number = len(commit_log)
    return current_commit_number


def example_generate_results_array(path_to_repo, output_folder):
    results_array = np.random.random((500, 3))
    np.savetxt(path_to_repo / output_folder / "result.csv", results_array, delimiter=",")
    return results_array


@tracks_results
def example_generate_results_with_options(repo, options):
    results_array = np.random.random((500, 3))
    np.savetxt(repo.output_path / "result.csv", results_array, delimiter=",")
    return results_array


def try_init_gitpython_repo(repo_path):
    Path(repo_path).exists()
    git.Repo(repo_path)
    return True


def try_initialize_git_repo(path_to_repo):
    if path_to_repo.exists():
        delete_path(path_to_repo)

    initialize_repo(path_to_repo, "results")

    assert try_init_gitpython_repo(path_to_repo)
    assert try_init_gitpython_repo(path_to_repo / "results")


def try_commit_code(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    current_commit_number = count_commit_number(repo)

    modify_code(path_to_repo)
    repo.commit("add code to print random number", add_all=True)

    updated_commit_number = count_commit_number(repo)
    assert current_commit_number + 1 == updated_commit_number


def try_commit_code_without_code_changes(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    current_commit_number = count_commit_number(repo)
    repo.commit("This commit will not be made", add_all=True)
    updated_commit_number = count_commit_number(repo)
    assert current_commit_number == updated_commit_number


def try_commit_results_data(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    current_commit_number = count_commit_number(repo.output_repo)
    with repo.track_results(results_commit_message="Add array") as output_branch:
        example_generate_results_array(path_to_repo, output_folder=repo.output_path)
    updated_commit_number = count_commit_number(repo.output_repo)
    assert current_commit_number <= updated_commit_number
    assert str(repo.output_repo.active_branch) == output_branch
    return output_branch


def try_commit_results_with_options(path_to_repo):
    options = Options()
    options.commit_message = "test with options"
    options.debug = False
    options.example = "123"
    options.dont_push = True

    repo = ProjectRepo(path_to_repo)
    current_commit_number = count_commit_number(repo.output_repo)

    example_generate_results_with_options(options, repo_path=repo.path)

    updated_commit_number = count_commit_number(repo.output_repo)
    assert current_commit_number <= updated_commit_number

    return str(repo.output_repo.active_branch)


def try_output_function(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    filepath = repo.output_path / "foo" / "bar"
    assert isinstance(filepath, Path)
    filepath = repo.output_data("foo/bar")
    assert isinstance(filepath, Path)


def try_print_log(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    repo.print_output_log()


def try_commit_results_with_uncommitted_code_changes(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    modify_code(path_to_repo)
    with pytest.raises(Exception):
        with repo.track_results(results_commit_message="Add array"):
            example_generate_results_array(path_to_repo, output_folder=repo.output_path)
    repo.commit("add code to print random number", add_all=True)


def try_load_previous_output(path_to_repo, branch_name):
    repo = ProjectRepo(path_to_repo)
    with repo.track_results(results_commit_message="Load array and extend"):
        cache_folder_path = repo.input_data(branch_name=branch_name)
        cached_array_path = cache_folder_path / "result.csv"
        previous_array = np.loadtxt(cached_array_path, delimiter=",")
        extended_array = np.concatenate([previous_array, previous_array])
        extended_array_file_path = path_to_repo / repo.output_path / "extended_result.csv"
        np.savetxt(extended_array_file_path,
                   extended_array,
                   delimiter=",")
        assert cached_array_path.exists()
        assert extended_array_file_path.exists()


def try_add_remote(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    repo.add_remote("git@jugit.fz-juelich.de:IBG-1/ModSim/cadet/CADET-RDM.git")
    assert "origin" in repo._git_repo.remotes


def try_initialize_from_remote():
    if Path("test_repo_from_remote").exists():
        delete_path("test_repo_from_remote")
    ProjectRepo.clone(
        url="git@github.com:ronald-jaepel/rdm_testing_template.git",
        to_path="test_repo_from_remote"
    )
    assert try_init_gitpython_repo("test_repo_from_remote")

    repo = ProjectRepo("test_repo_from_remote")
    assert hasattr(repo, "output_path")


def test_init_over_existing_repo(monkeypatch):
    path_to_repo = Path("test_repo_init_over_repo")
    if path_to_repo.exists():
        delete_path(path_to_repo)
    os.makedirs(path_to_repo)
    os.chdir(path_to_repo)
    os.system(f"git init --initial-branch=master")
    with open("README.md", "w") as handle:
        handle.write("Readme-line 1\n")
    with open(".gitignore", "w") as handle:
        handle.write("foo.bar.*")
    repo = git.Repo(".")
    repo.git.add(".")
    repo.git.commit("-m", "Initial commit")
    os.chdir("..")

    # using monkeypath to simulate user input
    monkeypatch.setattr('builtins.input', lambda x: "Y")

    initialize_repo(path_to_repo)
    delete_path(path_to_repo)


def test_init_over_existing_code(monkeypatch):
    path_to_repo = Path("test_repo_init_over_code")
    if path_to_repo.exists():
        delete_path(path_to_repo)
    os.makedirs(path_to_repo)

    with open(path_to_repo / "foobar.py", "w") as handle:
        handle.write("print('Hello World')\n")
    with open(path_to_repo / ".gitignore", "w") as handle:
        handle.write("foo.bar.*")

    # using monkeypath to simulate user input
    monkeypatch.setattr('builtins.input', lambda x: "Y")

    initialize_repo(path_to_repo)
    repo = git.Repo(path_to_repo)
    assert "Untracked files:" in repo.git.status()

    delete_path(path_to_repo)


def test_cache_with_non_rdm_repo(monkeypatch):
    path_to_repo = Path("non_rdm_repo")
    if path_to_repo.exists():
        delete_path(path_to_repo)
    os.makedirs(path_to_repo)
    os.chdir(path_to_repo)
    os.system(f"git init")
    with open("README.md", "w") as handle:
        handle.write("Readme-line 1\n")
    with open(".gitignore", "w") as handle:
        handle.write("foo.bar.*")
    git_repo = git.Repo(".")
    git_repo.git.add(".")
    git_repo.git.commit("-m", "Initial commit")

    os.chdir("..")
    if Path("test_repo_non_rdm_imports").exists():
        delete_path("test_repo_non_rdm_imports")
    initialize_repo("test_repo_non_rdm_imports")
    os.chdir("test_repo_non_rdm_imports")

    base_repo = BaseRepo(".")

    if Path("external_cache/non_rdm_repo").exists():
        delete_path("external_cache/non_rdm_repo")
    if Path("foo/bar/non_rdm_repo").exists():
        delete_path("foo/bar/non_rdm_repo")
    # import two repos and confirm verify works.
    base_repo.import_remote_repo(source_repo_location=".." / path_to_repo, source_repo_branch="master")
    base_repo.import_remote_repo(source_repo_location=".." / path_to_repo, source_repo_branch="master",
                            target_repo_location="foo/bar/non_rdm_repo")
    base_repo.verify_unchanged_cache()
    os.chdir("..")


def test_add_lfs_filetype():
    path_to_repo = Path("test_repo_add_lfs")
    if path_to_repo.exists():
        delete_path(path_to_repo)
    os.makedirs(path_to_repo)
    initialize_repo(path_to_repo)
    file_type = "*.bak"
    repo = ProjectRepo(path_to_repo)
    repo.output_repo.add_filetype_to_lfs(file_type)
    with open(repo.output_path / ".gitattributes", "r") as handle:
        gittatributes = handle.readlines()
    assert any(file_type in line for line in gittatributes)


def test_rdm_check():
    path_to_repo = Path("test_repo_rdm_check")
    new_project_url = "git@github.com:foobar/rdm_example_alternate.git"
    new_output_url = "git@github.com:foobar/rdm_example_output_alternate.git"
    if path_to_repo.exists():
        delete_path(path_to_repo)
    os.makedirs(path_to_repo)
    initialize_repo(path_to_repo)
    repo = ProjectRepo(path_to_repo)
    repo.add_remote("git@github.com:foobar/rdm_testing_template.git")
    repo.output_repo.add_remote("git@github.com:foobar/rdm_testing_template_output.git")
    repo.remote_set_url("origin", new_project_url)
    repo.output_repo.remote_set_url("origin", new_output_url)

    repo.check()
    with open(repo.path / "README.md", "r") as handle:
        readme_lines = handle.readlines()
    assert f'[output_repo]({ssh_url_to_http_url(new_output_url)})\n' in readme_lines
    with open(repo.output_repo.path / "README.md", "r") as handle:
        readme_lines = handle.readlines()
    assert f'[project_repo]({ssh_url_to_http_url(new_project_url)})\n' in readme_lines


def test_copy_external_data():
    path_to_source = Path("test_repo_external_data_source")
    if path_to_source.exists():
        delete_path(path_to_source)
    os.makedirs(path_to_source)

    filepath = path_to_source / f"static_data_contents"
    with open(filepath, "w") as file:
        file.write("This is static data")

    path_to_repo = Path("test_repo_external_data")
    if path_to_repo.exists():
        delete_path(path_to_repo)
    os.makedirs(path_to_repo)
    initialize_repo(path_to_repo)
    repo = ProjectRepo(path_to_repo)
    modify_code(path_to_repo)
    branch_name = repo.import_static_data(
        "test_repo_external_data_source",
        "import non_rdm_repo"
    )
    assert repo.has_uncomitted_changes
    cache_path = repo.copy_data_to_cache(branch_name)
    assert (cache_path / "test_repo_external_data_source" / "static_data_contents").exists()


def test_error_stack():
    path_to_repo = Path("test_repo_errors")
    if path_to_repo.exists():
        delete_path(path_to_repo)
    os.makedirs(path_to_repo)
    initialize_repo(path_to_repo)
    repo = ProjectRepo(path_to_repo)
    try:
        with repo.track_results("test error"):
            raise ValueError("This is an error message with \n a line break")
    except ValueError:
        pass
    with open("test_repo_errors/output/error.stack", "r") as handle:
        lines = handle.readlines()

    error_line = '    raise ValueError("This is an error message with \\n a line break")\n'
    assert error_line in lines


def test_cookiecutter_with_url(monkeypatch):
    path_to_repo = Path("test_repo_cookie")
    if path_to_repo.exists():
        delete_path(path_to_repo)
    os.makedirs(path_to_repo)

    # using monkeypatch to simulate user input
    # Mock console.input to simulate user input
    from rich.console import Console
    monkeypatch.setattr(Console, "input", lambda *args, **kwargs: "")

    initialize_repo(
        path_to_repo,
        cookiecutter_template="https://github.com/cadet/RDM-Cookiecutter-Example-Template.git"
    )
    assert (path_to_repo / "main.py").exists()


def test_cadet_rdm(path_to_repo):
    # because these depend on one-another and there is no native support afaik for sequential tests
    # these tests are called sequentially here as try_ functions.
    try_initialize_git_repo(path_to_repo)
    try_initialize_from_remote()

    try_add_remote(path_to_repo)
    # try_add_submodule(path_to_repo)
    try_commit_code(path_to_repo)
    try_commit_code_without_code_changes(path_to_repo)
    try_commit_results_with_uncommitted_code_changes(path_to_repo)
    try_output_function(path_to_repo)

    try_commit_results_with_options(path_to_repo)
    results_branch_name = try_commit_results_data(path_to_repo)
    try_print_log(path_to_repo)

    try_commit_code(path_to_repo)

    try_load_previous_output(path_to_repo, results_branch_name)


def test_with_detached_head():
    path_to_repo = Path("test_repo_2")
    if path_to_repo.exists():
        delete_path(path_to_repo)
    os.makedirs(path_to_repo)
    initialize_repo(path_to_repo)
    os.chdir(path_to_repo)
    for i in range(2):
        with open("README.md", "a") as handle:
            handle.write(f"Readme-line {i}\n")
        os.system(f"git add .")
        os.system(f"git commit -m foobar{i}")

    os.system("git checkout HEAD~1")
    repo = ProjectRepo(".")
    with repo.track_results("foo"):
        pass

    os.chdir("..")


# def test_with_external_repos():
#     path_to_repo = Path("test_repo_external_data")
#     if path_to_repo.exists():
#         delete_path(path_to_repo)
#     os.makedirs(path_to_repo)
#     initialize_repo(path_to_repo)
#
#     os.chdir(path_to_repo)
#
#     # to be able to hand over a valid branch, I first need to determine that branch
#     imported_repo = OutputRepo("../test_repo/results")
#     branch_name = imported_repo.active_branch.name
#
#     repo = ProjectRepo(".")
#
#     # import two repos and confirm verify works.
#     repo.import_remote_repo(source_repo_location="../test_repo/results", source_repo_branch=branch_name)
#     repo.import_remote_repo(source_repo_location="../test_repo/results", source_repo_branch=branch_name,
#                             target_repo_location="foo/bar/repo")
#     # delete folder and reload
#     delete_path("foo/bar/repo")
#
#     with pytest.raises(Exception):
#         repo.verify_unchanged_cache()
#
#     repo.fill_data_from_cadet_rdm_json()
#     repo.verify_unchanged_cache()
#
#     # Test if re_load correctly re_loads by modifying and then reloading
#     with open("external_cache/results/README.md", "w") as file_handle:
#         file_handle.writelines(["a", "b", "c"])
#     repo.fill_data_from_cadet_rdm_json(re_load=True)
#     repo.verify_unchanged_cache()
#
#     # modify file and confirm error raised
#     with open("external_cache/results/README.md", "w") as file_handle:
#         file_handle.writelines(["a", "b", "c"])
#     with pytest.raises(Exception):
#         repo.verify_unchanged_cache()
#
#     os.chdir("..")
