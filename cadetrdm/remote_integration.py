import gitlab


def load_token():
    """
    Read the API token from the .token file

    :return:
    """
    with open("../.token", "r") as file_handle:
        token = file_handle.readline()
    return token


def create_gitlab_remote(url, namespace, name):
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
