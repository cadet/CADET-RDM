from time import sleep

import git
import pytest

from cadetrdm import initialize_repo, ProjectRepo
from cadetrdm.io_utils import delete_path
from cadetrdm.remote_integration import GitHubRemote, GitLabRemote


@pytest.mark.server_api
def test_gitlab_create():
    url = "https://jugit.fz-juelich.de/"
    namespace = "r.jaepel"
    name = "API_test_project"
    remote = GitLabRemote()

    # ensure remote does not exist
    remote.delete_remote(url=url, namespace=namespace, name=name, username="r.jaepel")
    try:
        delete_path("test_repo_remote")
    except FileNotFoundError:
        pass

    sleep(3)

    response = remote.create_remote(url=url, namespace=namespace, name=name, username="r.jaepel")

    git.Repo.clone_from(response.ssh_url_to_repo, "test_repo_remote")
    delete_path("test_repo_remote")

    remote.delete_remote(url=url, namespace=namespace, name=name, username="r.jaepel")

    with pytest.raises(git.exc.GitCommandError):
        git.Repo.clone_from(response.ssh_url_to_repo, "test_repo_remote")


@pytest.mark.server_api
def test_github_create():
    namespace = "ronald-jaepel"
    name = "API_test_project"
    remote = GitHubRemote()

    # ensure remote does not exist
    try:
        remote.delete_remote(namespace=namespace, name=name, username="r.jaepel")
    except Exception:
        pass

    try:
        delete_path("test_repo_remote")
    except FileNotFoundError:
        pass

    sleep(3)

    response = remote.create_remote(namespace=namespace, name=name, username="r.jaepel")

    sleep(3)

    git.Repo.clone_from(response.html_url, "test_repo_remote")
    delete_path("test_repo_remote")

    remote.delete_remote(namespace=namespace, name=name, username="r.jaepel")

    with pytest.raises(git.exc.GitCommandError):
        git.Repo.clone_from(response.ssh_url, "test_repo_remote")


@pytest.mark.server_api
def test_repo_gitlab_integration():
    url = "https://jugit.fz-juelich.de/"
    namespace = "r.jaepel"
    name = "API_test_project"
    repo_name = "test_repo_remote"
    remote = GitLabRemote()

    # Clean up
    remote.delete_remote(url=url, namespace=namespace, name=name, username="r.jaepel")
    remote.delete_remote(url=url, namespace=namespace, name=name + "_output", username="r.jaepel")

    try:
        delete_path("test_repo_remote")
    except FileNotFoundError:
        pass

    initialize_repo(repo_name)

    repo = ProjectRepo(repo_name)
    repo.create_remotes(url=url, namespace=namespace, name=name, username="r.jaepel")

    assert repo.has_changes_upstream is False
