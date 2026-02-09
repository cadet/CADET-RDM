(python_interface)=
# Python interface

The Python interface exposes all CADET-RDM functionality for direct use within Python scripts, libraries, and interactive environments. It is suited for programmatic control, direct context tracking of code execution, and integration into existing Python workflows.

## Repository initialization

Create a new project repository or convert an existing directory into a CADET-RDM repository.

```python
from cadetrdm import initialize_repo

initialize_repo(path_to_repo, [output_directory_name])
```

Options:

- If no `path_to_repo` is provided, the repository is initialized in the root directory without creating a new directory.
- If `path_to_repo` is given as a relative path (e.g. "repository_name"), a new directory with that name is created inside the root directory.
- If `path_to_repo` is given as an absolute path (e.g.C:\Users\me\projects\myrepo), a new directory is created at the specified location.

Optionally, a `output_directory_name` can be given. Otherwise, it defaults to `output`.


### Cookiecutter support

Repositories can be initialized from Cookiecutter templates.

```python
from cadetrdm import initialize_repo

initialize_repo(path_to_repo, cookiecutter_template="template_url")
```

If `path_to_repo` is provided, it overrides any directory name specified by the Cookiecutter template.
If omitted, initialization happens in the current working directory.

## Handling results with CADET-RDM

### Tracking, committing and pushing results

Results are tracked using the `ProjectRepo` interface. All files written inside the tracking context are stored in a new output branch together with execution metadata.

```python
from cadetrdm import ProjectRepo

repo = ProjectRepo()
repo.commit("Commit code changes")

with repo.track_results(results_commit_message="Generate results"):
    data = generate_data()
    write_data_to_file(data, output_directory=repo.output_directory)

    analysis_results = analyse_data(data)
    plot_analysis_results(
        analysis_results,
        figure_path=repo.output_directory / "analysis" / "regression.png"
    )
```

Each execution creates a new output branch containing the generated results and associated metadata.

Project and output repositories can be pushed together using a single command.

```python
repo.push()
```

Consistency checks and staging are handled automatically by the Python interface before pushing.

### Reusing results from earlier runs

Each run is stored in an output branch named:

```
<timestamp>_<active_project_branch>_<project_repo_hash[:7]>
```

Reuse results from a previous run by loading them into the local cache:

```python
cached_folder_path = repo.input_data(branch_name="<branch_name>")
```

### Using results from another repository

Results from other CADET-RDM repositories can be imported and registered in the local cache.

```python
repo.import_remote_repo(
    source_repo_location="<URL>",
    source_repo_branch="<branch_name>"
)
```

Optionally, a destination directory can be specified:

```python
repo.import_remote_repo(
    source_repo_location="<URL>",
    source_repo_branch="<branch_name>",
    target_repo_location="<path/to/destination/repository>"
)
```

Repositories listed in `.cadet-rdm-cache.json` can be loaded with:

```python
repo.fill_data_from_cadet_rdm_json()
```

## Remote repositories

### Cloning repositories

Clone an existing CADET-RDM repository. This method must be used instead of `git clone` to ensure that both project and output repositories are initialized correctly.

```python
from cadetrdm import ProjectRepo

ProjectRepo.clone("<project_url>", "<destination_path>")
```

The destination directory must be empty.

### Adding existing remotes

Add remotes manually for both the project and output repositories.

```python
from cadetrdm import ProjectRepo

repo = ProjectRepo()
repo.add_remote("git@<my_git_server.foo>:<project>.git")
repo.output_repo.add_remote("git@<my_git_server.foo>:<project>_output.git")
```

### Creating remotes automatically

Remote repositories can be created automatically using the GitHub or GitLab APIs if a Personal Access Token is available in the Python keyring.

```python
from cadetrdm import ProjectRepo

repo = ProjectRepo()
repo.create_remotes(
    name="Workproject",
    namespace="githubusers_workproject",
    url="https://github.com/",
    username="githubuser"
)
```

The output repository name is derived automatically by appending `_output` to the project repository name.

### Migrating repositories

Migration to a different remote is performed by updating the `origin` URLs for both repositories and pushing the changes. This follows the same workflow as the command line interface.
