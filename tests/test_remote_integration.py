from types import SimpleNamespace

import pytest

from cadetrdm import ProjectRepo, initialize_repo
from cadetrdm.remote_integration import GitHubRemote, GitLabRemote


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def fake_github_repository(name, namespace=None, url=None, username=None):
    """Mimic the attributes of a PyGithub Repository."""
    return SimpleNamespace(ssh_url=f"git@github.com:{namespace}/{name}.git")


def fake_gitlab_project(url, namespace, name, username):
    """Mimic the attributes of a python-gitlab Project."""
    return SimpleNamespace(ssh_url_to_repo=f"git@gitlab.example.com:{namespace}/{name}.git")


@pytest.mark.parametrize(
    "remote_class, fake_create_remote, url, host",
    [
        (GitHubRemote, fake_github_repository, "https://api.github.com", "github.com"),
        (GitLabRemote, fake_gitlab_project, "https://gitlab.example.com/", "gitlab.example.com"),
    ],
)
def test_create_remotes_adds_ssh_urls(
    monkeypatch, remote_class, fake_create_remote, url, host
):
    monkeypatch.setattr(remote_class, "create_remote", staticmethod(fake_create_remote))
    initialize_repo("project")
    repo = ProjectRepo("project")

    repo.create_remotes(name="analysis", namespace="lab", url=url, username="me", push=False)

    assert repo.remote_urls == [f"git@{host}:lab/analysis.git"]
    assert repo.output_repo.remote_urls == [f"git@{host}:lab/analysis_output.git"]


def test_gitlab_delete_remote_only_deletes_exact_match(monkeypatch):
    projects = [
        SimpleNamespace(id=1, name="analysis", namespace={"full_path": "lab"}),
        SimpleNamespace(id=2, name="analysis_output", namespace={"full_path": "lab"}),
        SimpleNamespace(id=3, name="analysis", namespace={"full_path": "other-lab"}),
    ]
    deleted = []

    class FakeGitlab:
        def __init__(self, url, private_token):
            self.projects = SimpleNamespace(
                list=lambda **kwargs: projects,
                delete=deleted.append,
            )

    monkeypatch.setattr("cadetrdm.remote_integration.gitlab.Gitlab", FakeGitlab)
    monkeypatch.setattr(GitLabRemote, "load_token", staticmethod(lambda *args: "token"))

    GitLabRemote().delete_remote(
        url="https://gitlab.example.com/", namespace="Lab", name="analysis", username="me"
    )

    assert deleted == [1]
