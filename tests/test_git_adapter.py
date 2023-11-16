import os.path
import shutil
import stat
import random

import pytest
import git
import numpy as np

from cadetrdm import initialize_git_repo, ProjectRepo, initialize_from_remote


@pytest.fixture(scope="module")
def path_to_repo():
    # a "fixture" serves up shared, ready variables to test functions that should use the fixture as a kwarg
    return "test_repo"


# @pytest.fixture(scope="module", autouse=True)
# def my_fixture(path_to_repo):
#     print('INITIALIZATION')
#     if os.path.exists(path_to_repo):
#         remove_dir(path_to_repo)
#     yield "this is just here because something must yield"
#     print("TEAR DOWN")
#     remove_dir(path_to_repo)


def remove_dir(path_to_dir):
    def remove_readonly(func, path, exc_info):
        "Clear the readonly bit and reattempt the removal"
        # ERROR_ACCESS_DENIED = 5
        if func not in (os.unlink, os.rmdir) or exc_info[1].winerror != 5:
            raise exc_info[1]
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(path_to_dir, onerror=remove_readonly)


def modify_code(path_to_repo):
    # Add changes to the project code
    random_number = random.randint(0, 265)
    filepath = os.path.join(path_to_repo, f"print_random_number.py")
    with open(filepath, "w") as file:
        file.write(f"print({random_number})\n")


def count_commit_number(repo):
    commit_log = repo._git.log("--oneline").split("\n")
    current_commit_number = len(commit_log)
    return current_commit_number


def example_generate_results_array(path_to_repo, output_folder):
    results_array = np.random.random((500, 3))
    np.savetxt(os.path.join(path_to_repo, output_folder, "result.csv"),
               results_array,
               delimiter=",")
    return results_array


def try_init_gitpython_repo(repo_path):
    os.path.exists(repo_path)
    git.Repo(repo_path)
    return True


def try_initialize_git_repo(path_to_repo):
    if os.path.exists(path_to_repo):
        remove_dir(path_to_repo)

    initialize_git_repo(path_to_repo)

    assert try_init_gitpython_repo(path_to_repo)
    assert try_init_gitpython_repo(os.path.join(path_to_repo, "output"))


def try_commit_code(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    current_commit_number = count_commit_number(repo)

    modify_code(path_to_repo)
    repo.commit("add code to print random number", add_all=True)

    updated_commit_number = count_commit_number(repo)
    assert current_commit_number + 1 == updated_commit_number


def try_add_submodule(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    submodule_path = repo.load_external_repository("https://jugit.fz-juelich.de/IBG-1/ModSim/cadet/git_lfs_data_1")
    assert os.path.exists(submodule_path)


def try_commit_code_without_code_changes(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    current_commit_number = count_commit_number(repo)
    repo.commit("This commit will not be made", add_all=True)
    updated_commit_number = count_commit_number(repo)
    assert current_commit_number == updated_commit_number


def try_commit_results_data(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    current_commit_number = count_commit_number(repo.output_repo)
    with repo.track_results(results_commit_message="Add array"):
        example_generate_results_array(path_to_repo, output_folder=repo.output_folder)
    updated_commit_number = count_commit_number(repo.output_repo)
    assert current_commit_number <= updated_commit_number
    return str(repo.output_repo.active_branch)


def try_print_log(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    repo.print_output_log()


def try_commit_results_with_uncommitted_code_changes(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    modify_code(path_to_repo)
    with pytest.raises(Exception):
        with repo.track_results(results_commit_message="Add array"):
            example_generate_results_array(path_to_repo, output_folder=repo.output_folder)
    repo.commit("add code to print random number", add_all=True)


def try_load_previous_output(path_to_repo, branch_name):
    repo = ProjectRepo(path_to_repo)
    with repo.track_results(results_commit_message="Load array and extend"):
        cached_array_path = repo.input_data(branch_name=branch_name,
                                            file_path="result.csv")
        previous_array = np.loadtxt(cached_array_path, delimiter=",")
        extended_array = np.concatenate([previous_array, previous_array])
        extended_array_file_path = os.path.join(path_to_repo, repo.output_folder, "extended_result.csv")
        np.savetxt(extended_array_file_path,
                   extended_array,
                   delimiter=",")
        assert os.path.exists(cached_array_path)
        assert os.path.exists(extended_array_file_path)


def try_add_remote(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    repo.add_remote("git@jugit.fz-juelich.de:IBG-1/ModSim/cadet/CADET-RDM.git")
    assert "origin" in repo._git_repo.remotes


def try_initialize_from_remote():
    if os.path.exists("test_repo_from_remote"):
        remove_dir("test_repo_from_remote")
    initialize_from_remote("https://jugit.fz-juelich.de/IBG-1/ModSim/cadet/rdm-examples-fraunhofer-ime-aachen",
                           "test_repo_from_remote")
    assert try_init_gitpython_repo("test_repo_from_remote")


def test_init_over_existing_repo():
    path_to_repo = "test_repo_2"
    if os.path.exists(path_to_repo):
        remove_dir(path_to_repo)
    os.makedirs(path_to_repo)
    os.chdir(path_to_repo)
    os.system(f"git init")
    with open("README.md", "w") as handle:
        handle.write("Readme-line 1\n")
    with open(".gitignore", "w") as handle:
        handle.write("foo.bar.*")
    repo = git.Repo(".")
    repo.git.add(".")
    repo.git.commit("-m", "Initial commit")
    os.chdir("..")

    initialize_git_repo(path_to_repo)


def test_cadet_rdm(path_to_repo):
    # because these depend on one-another and there is no native support afaik for sequential tests
    # these tests are called sequentially here as try_ functions.
    try_initialize_git_repo(path_to_repo)
    # try_initialize_from_remote()

    try_add_remote(path_to_repo)
    # try_add_submodule(path_to_repo)
    try_commit_code(path_to_repo)
    try_commit_code_without_code_changes(path_to_repo)
    try_commit_results_with_uncommitted_code_changes(path_to_repo)

    results_branch_name = try_commit_results_data(path_to_repo)
    results_branch_name = try_commit_results_data(path_to_repo)
    try_print_log(path_to_repo)

    try_commit_code(path_to_repo)

    try_load_previous_output(path_to_repo, results_branch_name)
