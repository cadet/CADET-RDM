import gitlab
import github
import keyring
from abc import abstractmethod


class Remote:
    @staticmethod
    def load_token(url_options, username):
        token = None
        url_options = iter(url_options)
        try:
            while token is None:
                token = keyring.get_password(next(url_options), username)
        except StopIteration:
            raise RuntimeError(f"No token found in keyring for url {url_options[0]} and username {username}")

        return token

    @abstractmethod
    def create_remote(self, url, namespace, name, username):
        return

    @abstractmethod
    def delete_remote(self, url, namespace, name, username):
        return


class GitLabRemote(Remote):

    @property
    def url_fallbacks(self):
        return ["gitlab"]

    def create_remote(self, url, namespace, name, username):
        """
        Create remotes on gitlab within the given url / namespace / name. Use the token
        stored in the keyring under the username and url combination.

        :param namespace:
        :param name:
        :param url:
        :param username:
        :return:
        Query response
        """
        token = self.load_token([url] + self.url_fallbacks, username)
        gl = gitlab.Gitlab(url, private_token=token)

        namespace_id = gl.namespaces.list(get_all=True, search=namespace)[0].id
        response = gl.projects.create({"name": name, "namespace_id": namespace_id})
        return response

    def delete_remote(self, url, namespace, name, username):
        """
        Deletes remotes on gitlab within the given url / namespace / name. Use the token
        stored in the keyring under the username and url combination.

        :param namespace:
        :param name:
        :param url:
        :param username:
        :return:
        None
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

    @property
    def url_fallbacks(self):
        return ["https://github.com/", "https://github.com", "github", "github.com"]

    def create_remote(self, name, namespace=None, url="https://api.github.com", username=None):
        """
        Create remotes on GitHub within the given url / namespace / name. Use the token
        stored in the keyring under the username and url combination.

        :param namespace:
        :param name:
        :param url:
        :param username:
        :return:
        Query response
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

    def delete_remote(self, name, namespace, url="https://api.github.com", username=None):
        if username is None:
            username = namespace

        token = self.load_token([url] + self.url_fallbacks, username)

        auth = github.Auth.Token(token)
        g = github.Github(base_url=url, auth=auth)
        repo = g.get_repo(f"{namespace}/{name}")
        repo.delete()
