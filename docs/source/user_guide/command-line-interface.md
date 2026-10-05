# Command line interface (CLI)

The command line interface provides access to all CADET-RDM functionality via the `rdm` command. It is suited for scripted workflows, batch execution, and automation.

## Repository initialization

Create a new project repository or convert an existing directory into a CADET-RDM repository:

```bash
rdm init <path_to_repo> [output_directory_name]
```

Options:

- If no `<path_to_repo>` is provided, the repository is initialized in the root directory without creating a new directory.
- If `<path_to_repo>` is given as a relative path (e.g. "repository_name"), a new directory with that name is created inside the root directory.
- If `<path_to_repo>` is given as an absolute path (e.g. C:\Users\me\projects\myrepo), a new directory is created at the specified location.

Optionally, an `[output_directory_name]` can be given. Otherwise, it defaults to `output`.


### Cookiecutter support

Initialize a repository from a Cookiecutter template:

```bash
rdm init <path_to_repo> --cookiecutter <template_url>
```

If `<path_to_repo>` is provided, it overrides any directory name chosen in the Cookiecutter prompt.
If omitted, initialization happens in the current working directory.

## Handling results with CADET-RDM

### Running code and tracking results

Each execution creates a new output branch containing the generated results and associated metadata.

Run a Python script and track all generated results:

```bash
rdm run python <path/to/script.py> "commit message for the results"
```

Run an arbitrary command, for example a bash script:

```bash
rdm run command "bash run_simulation.sh" "commit message for the results"
```

The command must be enclosed in quotes.

### Staging, committing, and pushing changes

Check repository consistency:

```bash
rdm check
```

`rdm check` updates the links between the project and output repositories in both READMEs and in `.cadet-rdm-data.json`, and commits the changes.
With `--no-commit`, the changes in the project repository are staged instead of committed, and with `--project-only`, the output repository is left untouched.

Commits made through CADET-RDM update these links automatically.
To also keep them up to date when committing with plain git, e.g. after changing a remote with `git remote set-url`, add the `rdm-check` hook to the `.pre-commit-config.yaml` of the project repository:

```yaml
repos:
-   repo: https://github.com/cadet/CADET-RDM
    rev: v1.2.0
    hooks:
    -   id: rdm-check
```

and install it with `pre-commit install`.
The hook is optional and never blocks a commit.
It runs `rdm check --no-commit --project-only --warn-only` before every commit, so updated links are included in the commit.
If the check fails, e.g. because git-lfs is not installed, it prints a warning and the commit proceeds.

Stage changes:

```bash
rdm add <filepath>
```

Commit staged changes (option: setting `-a` will stage all changes and commit them):

```bash
rdm commit -m <message> [-a]
```

Push both project and output repositories:

```bash
rdm push
```

Push only the output repository, e.g. to publish results without pushing unfinished project changes:

```bash
rdm push --output-only
```

### Reusing results from earlier runs

Each run is stored in an output branch named:

```
<timestamp>_<active_project_branch>_<project_repo_hash[:7]>
```

Cache results locally:

```bash
rdm data cache <branch_name>
```

### Using results from another repository

Fetch repositories listed in `.cadet-rdm-cache.json`:

```bash
rdm data fetch
```

## Remote repositories

### Cloning repositories

Clone an existing CADET-RDM repository:

```bash
rdm clone <project_url> <destination_path>
```

The destination directory must be empty.

### Adding existing remotes

Add remotes manually in both repositories:

```bash
rdm remote add git@<my_git_server.foo>:<project>.git
cd output
rdm remote add git@<my_git_server.foo>:<project>_output.git
```

### Creating remotes automatically

Create project and output remotes using the GitHub or GitLab APIs:

```bash
rdm remote create <url> <namespace> <name> <username>
```

Example:

```bash
rdm remote create https://github.com/ githubusers_workproject Workproject githubuser
```

The output repository name is derived automatically by appending `_output` to the project repository name.

### Migrating repositories

Update the `origin` remote for both repositories and push:

```bash
rdm remote set-url origin git@<my_git_server.foo>:<project>.git
cd output
rdm remote set-url origin git@<my_git_server.foo>:<project>_output.git
cd ..
rdm push
```
