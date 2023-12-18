
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

You can create remotes for both the project and the output repository with one command, using the GitLab or GitHub API.

This requires you to have created a 
[GitLab Personal Access Token (PAT)](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html)
and to store it in the `.token` file in the project's root. Then you can run:

```python
repo.create_gitlab_remotes(
    name="e.g. API_test_project",
    namespace="e.g. r.jaepel",
    url="e.g. https://jugit.fz-juelich.de/",
)
```

or

```bash
cadet-rdm create-gitlab-remotes API_test_project r.jaepel https://jugit.fz-juelich.de/
```

Both functions are also available for the GitHub API:
`repo.create_github_remotes(name, namespace)` and ` cadet-rdm create-github-remotes name namespace`.

## Extending GIT-LFS scope

Several common datatypes are included in GIT-LFS by default. These currently are
`"*.jpg", "*.png", "*.xlsx", "*.h5", "*.ipynb", "*.pdf", "*.docx", "*.zip", "*.html"`

You can add datatypes you require by running:

````python
repo.add_filetype_to_lfs("*.npy")
````

or

```bash
cadet-rdm add_filetype_to_lfs *.npy
```
