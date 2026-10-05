from typing import Any, Iterable

import gitlab
import github
import keyring
from abc import abstractmethod


class Remote:
    """Interface for creating and deleting repositories on a git hosting service."""

    @staticmethod
    def load_token(url_options: Iterable[str], username: str) -> str:
        """
        Load an access token from the keyring.

        Parameters
        ----------
        url_options : Iterable[str]
            Keyring service names to try, in order.
        username : str
            Username the token is stored under.

        Returns
        -------
        str
            The first token found.

        Raises
        ------
        RuntimeError
            If no token is stored for any of the services.
        """
        token = None
        url_options_iter = iter(url_options)
        try:
            while token is None:
                token = keyring.get_password(next(url_options_iter), username)
        except StopIteration:
            raise RuntimeError(
                f"No token found in keyring for url {url_options} and username {username}"
            )

        return token

    @abstractmethod
    def create_remote(self, url: str, namespace: str, name: str, username: str) -> Any:
        """Create a remote repository."""
        return

    @abstractmethod
    def delete_remote(self, url: str, namespace: str, name: str, username: str) -> None:
        """Delete a remote repository."""
        return


class GitLabRemote(Remote):
    """Remote repositories on a GitLab instance."""

    @property
    def url_fallbacks(self) -> list[str]:
        """Keyring service names tried after the instance URL."""
        return ["gitlab"]

    def create_remote(self, url: str, namespace: str, name: str, username: str) -> Any:
        """
        Create a remote on GitLab within the given url / namespace / name.

        Use the token stored in the keyring under the username and url combination.

        Parameters
        ----------
        url : str
            URL of the GitLab instance.
        namespace : str
            Group or user namespace of the new project.
        name : str
            Name of the new project.
        username : str
            Username the token is stored under.

        Returns
        -------
        Any
            Query response.
        """
        namespace = namespace.lower()
        token = self.load_token([url] + self.url_fallbacks, username)
        gl = gitlab.Gitlab(url, private_token=token)
        # We need the groups list, because for some ineffable reason, gitlab doesn't
        # always give all namespaces. This assumes, that the group_id and the
        # corresponding namespace_id are identical. So far this has been true.
        gl_groups = gl.groups.list(get_all=True)
        # We also need the namespace list for the personal namespace.
        gl_namespaces = gl.namespaces.list(get_all=True)
        matching_namespace = [gl_group for gl_group in gl_groups + gl_namespaces
                              if gl_group.full_path.lower() == namespace]

        if len(matching_namespace) == 0:
            raise ValueError(f"Could not find namespace {namespace} "
                             f"in {[gl_namespace.full_path for gl_namespace in gl_groups]}")
        if len(matching_namespace) >= 2:
            matching_namespace_id_set = set({group.id for group in matching_namespace})
            if len(matching_namespace_id_set) > 1:
                raise ValueError(
                    f"Not unique namespace {namespace} "
                    f"in {[gl_namespace.full_path.lower() for gl_namespace in gl_groups]}"
                )

        namespace_id = matching_namespace[0].id

        response = gl.projects.create({"name": name, "namespace_id": namespace_id})
        return response

    def delete_remote(self, url: str, namespace: str, name: str, username: str) -> None:
        """
        Delete remotes on GitLab within the given url / namespace / name.

        Use the token stored in the keyring under the username and url combination.

        Parameters
        ----------
        url : str
            URL of the GitLab instance.
        namespace : str
            Namespace of the project.
        name : str
            Name of the project.
        username : str
            Username the token is stored under.
        """
        token = self.load_token([url] + self.url_fallbacks, username)
        gl = gitlab.Gitlab(url, private_token=token)

        potential_projects = gl.projects.list(get_all=True, search=[namespace, name])

        for project in potential_projects:
            if project.name != name:
                pass
            if project.namespace["name"] != namespace:
                pass

            gl.projects.delete(project.id)
        return


class GitHubRemote(Remote):
    """Remote repositories on GitHub."""

    @property
    def url_fallbacks(self) -> list[str]:
        """Keyring service names tried after the API URL."""
        return ["https://github.com/", "https://github.com", "github", "github.com"]

    def create_remote(
        self,
        name: str,
        namespace: str | None = None,
        url: str = "https://api.github.com",
        username: str | None = None,
    ) -> Any:
        """
        Create a remote on GitHub within the given url / namespace / name.

        Use the token stored in the keyring under the username and url combination.

        Parameters
        ----------
        name : str
            Name of the new repository.
        namespace : str | None, optional
            User or organization.
            If None, the repository is created for the authenticated user.
        url : str, optional
            URL of the GitHub API.
        username : str | None, optional
            Username the token is stored under. Defaults to the namespace.

        Returns
        -------
        Any
            Query response.
        """
        if username is None and namespace is not None:
            username = namespace

        token = self.load_token([url] + self.url_fallbacks, username)

        auth = github.Auth.Token(token)
        g = github.Github(base_url=url, auth=auth)
        user = g.get_user()

        if namespace is None or namespace == user.login:
            base = user
        else:
            try:
                organization = g.get_organization(namespace)
                base = organization
            except github.GithubException:
                raise RuntimeError(f"No organization or user named {namespace} found in {url}")

        response = base.create_repo(
            name,
            allow_rebase_merge=True,
            auto_init=False,
            has_issues=True,
            has_projects=False,
            has_wiki=False,
            private=False,
        )
        return response

    def delete_remote(
        self,
        name: str,
        namespace: str,
        url: str = "https://api.github.com",
        username: str | None = None,
    ) -> None:
        """
        Delete a remote on GitHub.

        Parameters
        ----------
        name : str
            Name of the repository.
        namespace : str
            User or organization owning the repository.
        url : str, optional
            URL of the GitHub API.
        username : str | None, optional
            Username the token is stored under. Defaults to the namespace.
        """
        if username is None:
            username = namespace

        token = self.load_token([url] + self.url_fallbacks, username)

        auth = github.Auth.Token(token)
        g = github.Github(base_url=url, auth=auth)
        repo = g.get_repo(f"{namespace}/{name}")
        repo.delete()
