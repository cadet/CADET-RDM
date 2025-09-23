
# Using the Command Line Interface (CLI)

## Initialize Project Repository

Create a new project repository or convert an existing repository into a CADET-RDM repo:

```bash
rdm init <path-to-repo>
```


The `output_directory_name` can be given optionally. It defaults to `output`.


## Executing scripts

You can execute python files or arbitray commands using the CLI:

```bash
cd path/to/your/project
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

You can use this file to load the remote repositories based on the cache.json with

```bash
rdm data fetch
```

## Cloning rdm repositories

You should use `cadet-rdm clone` instead of `git clone` to clone an existing rdm repository to a new location. The destination directory must be empty. 

```bash
rdm clone <project_url> <destination_path>
```


## Sharing Results

To share your project code and results (`output`) with others, you need to create remote repositories on e.g.
[GitHub](https://github.com/) or GitLab. You need to create a remote for both the _project_ repository and the
_output_ repository.

Once created, the remotes need to be added to the local repositories.

```bash
rdm remote add git@<my_git_server.foo>:<project>.git
cd output
rdm remote add git@<my_git_server.foo>:<project>_output.git
```

Once remotes are configured, you can push all changes to the project repository and the output repository with the following command from within the project repository:

```bash
rdm push
```

## Migrating a repository

If you want to migrate a repository to another remote, the easiest way to do that at the moment is to create the remote
repositories on GitHub or GitLab and change the `origin` URL for the project and output repositories with:

```bash
rdm remote set-url origin git@<my_git_server.foo>:<project>.git
cd output
rdm remote set-url origin git@<my_git_server.foo>:<project>_output.git
cd ..
rdm push
```
