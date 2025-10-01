
# Command line interface (CLI)

## Initialize Project Repository

Create a new project repository or convert an existing repository into a CADET-RDM repository:

```bash
rdm init <path-to-repo>
```
- If no `<path-to-repo>` is provided, the repository is initialized in the root directory without creating a new directory.
- If `<path-to-repo>` is given as a relative path (e.g. "repository_name"), a new directory with that name is created inside the root directory.
- If `<path-to-repo>` is given as an absolute path (e.g. C:\Users\me\projects\myrepo), a new directory is created at the specified location.

The `output_directory_name` can be given optionally. It defaults to `output`.


## Executing scripts

Python files or arbitray commands can be executed using the CLI:

```bash
cd path/to/project_repository
rdm run_yml python <path/to/file> "commit message for the results"
rdm run_yml command "command as it would be run" "commit message for the results"
```

For the run-command option, the command must be given in quotes, so:

```bash
rdm run_yml command "python example_file.py" "commit message for the results"
```

## Re-using results from previous iterations

Each result stored with CADET-RDM is given a unique branch name within the output directory, formatted as:
`<timestamp>_<active_project_branch>_<project_repo_hash[:7]>`

With this branch name, previously generated data can be loaded in as input data for
further calculations. The following command will copy the contents of the `branch_name` branch to the
cache directory at `project_root/output_cached/branch_name`.

```bash
rdm data cache branch_name
```

## Using results from another repository

The Project repository URL, branch_name and location of results can be stored in the .cadet-rdm-cache.json file, like this:

```json
{
  "__example/path/to/repo__": {
    "source_repo_location": "git@jugit.fz-juelich.de:IBG-1/ModSim/cadet/agile_cadet_rdm_presentation_output.git",
    "branch_name": "output_from_master_3910c84_2023-10-25_00-17-23",
    "commit_hash": "6e3c26527999036e9490d2d86251258fe81d46dc"
  }
}
```

This cache.json file can be used to load remote repositories.

```bash
rdm data fetch
```

## Cloning rdm repositories

The command `rdm clone` should be used instead of `git clone` to clone an existing rdm repository to a new location. The destination directory must be empty.

```bash
rdm clone <project_url> <destination_path>
```


## Sharing Results

To share the project code and results (`output`) with others, remote repositories have to be configured on e.g.
[GitHub](https://github.com/) or GitLab. Remotes for both the _project_ repository and the
_output_ repository have to be created.

Once created, the remotes need to be added to the local repositories.

```bash
rdm remote add git@<my_git_server.foo>:<project>.git
cd output
rdm remote add git@<my_git_server.foo>:<project>_output.git
```

Once remotes are configured, all changes to the project repository and the output repository can be pushed with the following command from within the project repository:

```bash
rdm push
```

## Migrating a repository

The easiest way to migrate a repository to another remote, is to create the remote
repositories on GitHub or GitLab and change the `origin` URL for the project and output repositories with:

```bash
rdm remote set-url origin git@<my_git_server.foo>:<project>.git
cd output
rdm remote set-url origin git@<my_git_server.foo>:<project>_output.git
cd ..
rdm push
```
