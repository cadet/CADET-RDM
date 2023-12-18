
# Getting started

## Initialize Project Repository

Create a new project repository or convert an existing repository into a CADET-RDM repo:

```bash
cadet-rdm initialize-repo <path-to-repo>
```

or from python

```python
from cadetrdm import initialize_repo

initialize_repo(path_to_repo)
```

The `output_folder_name` can be given optionally. It defaults to `output`.

## Creating and adding remotes

You can create remotes for both the project and the output repository with one command, using the GitLab API. 
Support for the GitHub API will be added in the future.

This requires you to have created a 
[GitLab Personal Access Token (PAT)](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html)
and to store it in the `.token` file in the project's root. Then you can run:

```python
repo.create_gitlab_remotes(
    url="e.g. https://jugit.fz-juelich.de/",
    namespace="e.g. r.jaepel",
    name="e.g. API_test_project"
)
```
