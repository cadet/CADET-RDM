"""
Tests that create and delete repositories through the GitLab and GitHub APIs.

They are marked `server_api` and need an account, a token in the Python keyring and
SSH access to the host. Configure the accounts with environment variables; tests for
a host whose namespace is not set are skipped:

- CADET_RDM_TEST_GITLAB_URL: GitLab instance (default: https://jugit.fz-juelich.de/)
- CADET_RDM_TEST_GITLAB_NAMESPACE: user or group to create test projects in
- CADET_RDM_TEST_GITLAB_USERNAME: keyring username of the token (default: namespace)
- CADET_RDM_TEST_GITHUB_NAMESPACE: user or organization to create test repositories in
- CADET_RDM_TEST_GITHUB_USERNAME: keyring username of the token (default: namespace)
"""

import os
import uuid
from dataclasses import dataclass
from time import sleep

import git
import pytest

from cadetrdm import initialize_repo, ProjectRepo
from cadetrdm.remote_integration import GitHubRemote, GitLabRemote, Remote
from cadetrdm.repositories import BaseRepo

GITHUB_API_URL = "https://api.github.com"


@dataclass
class Account:
    url: str
    namespace: str
    username: str


def account_from_environment(host: str, default_url: str) -> Account:
    namespace = os.environ.get(f"CADET_RDM_TEST_{host}_NAMESPACE")
    if not namespace:
        pytest.skip(f"Set CADET_RDM_TEST_{host}_NAMESPACE to run {host} API tests.")
    return Account(
        url=os.environ.get(f"CADET_RDM_TEST_{host}_URL", default_url),
        namespace=namespace,
        username=os.environ.get(f"CADET_RDM_TEST_{host}_USERNAME", namespace),
    )


@pytest.fixture
def gitlab_account():
    return account_from_environment("GITLAB", "https://jugit.fz-juelich.de/")


@pytest.fixture
def github_account():
    return account_from_environment("GITHUB", GITHUB_API_URL)


@pytest.fixture
def repo_name():
    return f"cadet_rdm_api_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def delete_quietly(remote: Remote, account: Account, name: str) -> None:
    try:
        remote.delete_remote(
            url=account.url, namespace=account.namespace, name=name, username=account.username
        )
    except Exception:
        pass


@pytest.mark.server_api
@pytest.mark.parametrize("host", ["gitlab", "github"])
def test_create_and_delete_remote(host, repo_name, request):
    account = request.getfixturevalue(f"{host}_account")
    remote = GitLabRemote() if host == "gitlab" else GitHubRemote()

    try:
        response = remote.create_remote(
            url=account.url,
            namespace=account.namespace,
            name=repo_name,
            username=account.username,
        )
        sleep(3)
        BaseRepo.clone(remote.ssh_url(response), "cloned_remote")
    finally:
        delete_quietly(remote, account, repo_name)

    sleep(3)
    with pytest.raises(git.exc.GitCommandError):
        BaseRepo.clone(remote.ssh_url(response), "cloned_after_delete")


@pytest.mark.server_api
@pytest.mark.parametrize("host", ["gitlab", "github"])
def test_create_remotes_for_project(host, repo_name, request):
    account = request.getfixturevalue(f"{host}_account")
    remote = GitLabRemote() if host == "gitlab" else GitHubRemote()

    initialize_repo("project")
    repo = ProjectRepo("project")
    try:
        repo.create_remotes(
            url=account.url,
            namespace=account.namespace,
            name=repo_name,
            username=account.username,
        )

        assert len(repo.remote_urls) == 1
        assert len(repo.output_repo.remote_urls) == 1
        assert repo.has_changes_upstream is False
    finally:
        delete_quietly(remote, account, repo_name)
        delete_quietly(remote, account, repo_name + "_output")
