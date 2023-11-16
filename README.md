# The CADET-Research Data Management toolbox

## Getting started
### Installation
CADET-RDM can be installed using

```pip install cadetrdm```

### Initialize Project Repository
Create a new project repository or convert an existing repository into a CADET-RDM repo:

```bash
cadet-rdm initialize-repo <path-to-repo> <output-folder-name>
```
or from python

```python
from cadetrdm import initialize_repo
initialize_repo(path_to_repo, output_folder_name)
```

The `output_folder_name` can be given optionally. It defaults to `output`.

### Use CADET-RDM in Python
#### Tracking Results

```python
from cadetrdm import ProjectRepo

"""
Your imports and function declarations
e.g. generate_data(), write_data_to_file(), analyse_data() and plot_analysis_results()
"""

if __name__ == '__main__':
    # Instantiate CADET-RDM ProjectRepo handler
    repo = ProjectRepo()

    # If you've made changes to the code, commit the changes
    repo.commit("Add code to generate and analyse example data")

    # Everything written to the output_folder within this context manager gets tracked
    # The method repo.output_data() generates full paths to within your output_folder
    with repo.track_results(results_commit_message="Generate and analyse example data"):
        data = generate_data()
        output_filepath = repo.output_data(sub_path="raw_data/data.csv")
        write_data_to_file(data, output_filepath)

        analysis_results = analyse_data(data)
        figure_path=repo.output_data("analysis/regression.png")
        plot_analysis_results(analysis_results, figure_path)

```

#### Sharing Results

To share your project code and results with others, you need to create remote repositories on e.g. 
[GitHub](https://github.com/) or GitLab. You need to create a remote for both the _project_ repo and the
_results_ repo.

Once created, the remotes need to be added to the local repositories.

```bash
cadet-cli add-remote-to-repo <path_to_repo> git@<my_git_server.foo>:<project>.git
cadet-cli add-remote-to-repo <path_to_repo/output_folder> git@<my_git_server.foo>:<project>_output.git
```
or in Python:

```python
repo = ProjectRepo()
repo.add_remote("git@<my_git_server.foo>:<project>.git")
repo.output_repo.add_remote("git@<my_git_server.foo>:<project>_output.git")
```

Once remotes are configured, you can push all changes to the project repo and the results repos with the 
command

```python
# push all changes to the Project and Output repositories with one command:
repo.push()
```


#### Re-using results from previous iterations

Each result stored with CADET-RDM is given a unique branch name, formatted as:
`<timestamp>_<output_folder>_"from"_<active_project_branch>_<project_repo_hash[:7]>`

With this branch name, previously generated data can be loaded in as input data for 
further calculations.

```python
cached_array_path = repo.input_data(branch_name=branch_name, file_path="raw_data/data.csv")
```

Alternatively, using the auto-generated cache of previous results, CADET-RDM can infer
the correct branch name from the path to the file within the cache

```python
cached_array_path = repo.input_data(file_path="output_cached/<branch_name>/raw_data/data.csv")
```


