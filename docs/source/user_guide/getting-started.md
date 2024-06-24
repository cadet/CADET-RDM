
# Getting started

## Initialize Project Repository

Create a new project repository or convert an existing repository into a CADET-RDM repo:

```bash
rdm init <path-to-repo>
```

or from python

```python
from cadetrdm import initialize_repo

initialize_repo(path_to_repo)
```

The `output_folder_name` can be given optionally. It defaults to `output`.

## Creating and adding remotes

You can create remotes for both the project and the output repository with one command, using the GitLab or GitHub API.

You need to create a
[GitLab Personal Access Token (PAT)](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) or [GitHub PAT](https://github.com/settings/tokens?type=beta) with api access rights
and store it in the Python `keyring` using an interactive Python session:

```python
import keyring

keyring.set_password("e.g. https://jugit.fz-juelich.de/", username, token)
```

or in a command line

````commandline
keyring set system username
````

Then you can run:

```python
from cadetrdm import ProjectRepo

repo = ProjectRepo()

repo.create_remotes(
    name="e.g. API_test_project",
    namespace="e.g. r.jaepel",
    url="e.g. https://jugit.fz-juelich.de/",
    username="e.g. r.jaepel"
)
```

or in a command line

```bash
rdm remote create url namespace name username
rdm remote create https://jugit.fz-juelich.de/ r.jaepel API_test_project r.jaepel
```


## Extending GIT-LFS scope

Several common datatypes are included in GIT-LFS by default. These currently are
`"*.jpg", "*.png", "*.xlsx", "*.h5", "*.ipynb", "*.pdf", "*.docx", "*.zip", "*.html"`

You can add datatypes you require by running:

````python
from cadetrdm import ProjectRepo

repo = ProjectRepo()

repo.output_repo.add_filetype_to_lfs("*.npy")
````


or from within the output folder in a command line:

```bash
rdm lfs add *.npy
```
