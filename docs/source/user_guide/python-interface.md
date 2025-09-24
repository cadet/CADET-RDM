(python_interface)=
# Python interface

## Tracking Results

```python
from cadetrdm import ProjectRepo

"""
Imports and function declarations
e.g. generate_data(), write_data_to_file(), analyse_data() and plot_analysis_results()
"""

if __name__ == '__main__':
    # Instantiate CADET-RDM ProjectRepo handler
    repo = ProjectRepo()

    # Commit all changes to the code
    repo.commit("Add code to generate and analyse example data")

    # Everything written to the output_directory within this context manager gets tracked
    # The method repo.output_data() generates full paths to within the output_directory
    with repo.track_results(results_commit_message="Generate and analyse example data"):
        data = generate_data()
        write_data_to_file(data, output_directory=repo.output_directory)

        analysis_results = analyse_data(data)
        plot_analysis_results(analysis_results, figure_path=repo.output_directory / "analysis" / "regression.png")

```

## Sharing Results

To share the project code and results (`output`) with others, remote repositories have to be configured on e.g.
[GitHub](https://github.com/) or GitLab. Remotes for both the _project_ repository and the
_output_ repository have to be created.

Once created, the remotes need to be added to the local repositories.

```python
repo = ProjectRepo()
repo.add_remote("git@<my_git_server.foo>:<project>.git")
repo.output_repo.add_remote("git@<my_git_server.foo>:<project>_output.git")
```

Once remotes are configured, all changes to the project repository and the output repository can be pushed with the following command from within the project repository:

```python
# push all changes to the Project and Output repositories with one command:
repo.push()
```

## Re-using results from previous iterations

Each result stored with CADET-RDM is given a unique branch name, formatted as:
`<timestamp>_<active_project_branch>_<project_repo_hash[:7]>`

With this branch name, previously generated data can be loaded in as input data for
further calculations.

```python
cached_folder_path = repo.input_data(branch_name=branch_name)
```


```json
{
  "__example/path/to/repo__": {
    "source_repo_location": "git@jugit.fz-juelich.de:IBG-1/ModSim/cadet/agile_cadet_rdm_presentation_output.git",
    "branch_name": "output_from_master_3910c84_2023-10-25_00-17-23",
    "commit_hash": "6e3c26527999036e9490d2d86251258fe81d46dc"
  }
}
```

## Using results from another repository

The results from another repository can be to used by loading them into the target project with:

```python
repo.import_remote_repo(source_repo_location="<URL>", source_repo_branch="<branch_name>")
repo.import_remote_repo(source_repo_location="<URL>", source_repo_branch="<branch_name>",
                        target_repo_location="<path/to/destination/repository>")
```

This will store the URL, branch_name and location in the .cadet-rdm-cache.json file, like this:

```json
{
  "__example/path/to/repo__": {
    "source_repo_location": "git@jugit.fz-juelich.de:IBG-1/ModSim/cadet/agile_cadet_rdm_presentation_output.git",
    "branch_name": "output_from_master_3910c84_2023-10-25_00-17-23",
    "commit_hash": "6e3c26527999036e9490d2d86251258fe81d46dc"
  }
}
```

This file can be used to load remote repositories based on the cache.json with

```python
repo.fill_data_from_cadet_rdm_json()
```

## Cloning from remote

The method `cadetrdm.ProjectRepo.clone()` should be used instead of `git clone` to clone an rdm repository to a new location.

```python
from cadetrdm import ProjectRepo

ProjectRepo.clone("<project_URL>, <destination_path>")
```
