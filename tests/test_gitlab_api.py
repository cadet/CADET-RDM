from time import sleep

import git
import pytest

from cadetrdm import initialize_repo, ProjectRepo
from cadetrdm.io_utils import delete_path

from cadetrdm.remote_integration import delete_gitlab_remote, create_gitlab_remote


def test_gitlab_create():
    url = "https://jugit.fz-juelich.de/"
    namespace = "r.jaepel"
    name = "API_test_project"

    # ensure remote does not exist
    delete_gitlab_remote(url=url, namespace=namespace, name=name)
    try:
        delete_path("test_repo_remote")
    except FileNotFoundError:
        pass

    sleep(3)

    response = create_gitlab_remote(url=url, namespace=namespace, name=name)

    git.Repo.clone_from(response.ssh_url_to_repo, "test_repo_remote")
    delete_path("test_repo_remote")

    delete_gitlab_remote(url=url, namespace=namespace, name=name)

    with pytest.raises(git.exc.GitCommandError):
        git.Repo.clone_from(response.ssh_url_to_repo, "test_repo_remote")


def test_repo_gitlab_integration():
    url = "https://jugit.fz-juelich.de/"
    namespace = "r.jaepel"
    name = "API_test_project"
    repo_name = "test_repo_remote"

    # Clean up
    delete_gitlab_remote(url=url, namespace=namespace, name=name)
    delete_gitlab_remote(url=url, namespace=namespace, name=name + "_output")

    try:
        delete_path("test_repo_remote")
    except FileNotFoundError:
        pass

    initialize_repo(repo_name)

    repo = ProjectRepo(repo_name)
    repo.create_gitlab_remotes(url=url, namespace=namespace, name=name)
