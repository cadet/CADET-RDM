import gitlab
import github


def load_token():
    """
    Read the API token from the .token file

    :return:
    """
    with open("../.token", "r") as file_handle:
        token = file_handle.readline()
    return token


def create_gitlab_remote(namespace, name, url=None):
    token = load_token()

    gl = gitlab.Gitlab(url, private_token=token)

    namespace_id = gl.namespaces.list(get_all=True, search=namespace)[0].id
    response = gl.projects.create({"name": name, "namespace_id": namespace_id})
    return response


def delete_gitlab_remote(url, namespace, name):
    token = load_token()

    gl = gitlab.Gitlab(url, private_token=token)

    potential_projects = gl.projects.list(get_all=True, search=[namespace, name])

    for project in potential_projects:
        if project.name != name:
            pass
        if project.namespace["name"] != namespace:
            pass

        gl.projects.delete(project.id)


def create_github_remote(name, namespace=None, url="https://api.github.com"):
    token = load_token()

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


def delete_github_remote(name, namespace, url="https://api.github.com"):
    token = load_token()

    auth = github.Auth.Token(token)
    g = github.Github(base_url=url, auth=auth)
    repo = g.get_repo(f"{namespace}/{name}")
    repo.delete()
