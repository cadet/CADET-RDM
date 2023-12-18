
# CLI Interface

## Initialize Project Repository

Create a new project repository or convert an existing repository into a CADET-RDM repo:

```bash
cadet-rdm initialize-repo <path-to-repo>
```


The `output_folder_name` can be given optionally. It defaults to `output`.


## Executing scripts

You can execute python files or arbitray commands using the CLI:

```bash
cd path/to/your/project
cadet-rdm run-python-file <path/to/file> "commit message for the results"
cadet-rdm run-command "command as it would be run" "commit message for the results"
```

For the run-command option, the command must be given in quotes, so:

```bash
cadet-rdm run-command "python example_file.py" "commit message for the results"
```


## Using results from another repository

You can load in results from another repository to use in your project using the CLI:

```bash
cd path/to/your/project
cadet-rdm import-remote-repo <URL> <branch_name>
cadet-rdm import-remote-repo <URL> <branch_name> --target_repo_location <path/to/where/you/want/it>
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

You can use this file to load the remote repositories based on the cache.json with

```bash
cadet-rdm fill-data-from-cadet-rdm-json
```

## Cloning from remote

You should use `cadet-rdm clone` instead of `git clone` to clone the repo to a new location.

```bash
cadet-rdm clone <URL> <path/to/repo>
```


## Sharing Results

To share your project code and results with others, you need to create remote repositories on e.g.
[GitHub](https://github.com/) or GitLab. You need to create a remote for both the _project_ repo and the
_results_ repo.

Once created, the remotes need to be added to the local repositories.

```bash
cadet-rdm add-remote-to-repo git@<my_git_server.foo>:<project>.git
cadet-rdm --path_to_repo output add-remote-to-repo git@<my_git_server.foo>:<project>_output.git
```

Once remotes are configured, you can push all changes to the project repo and the results repos with the
command

```bash
cadet-rdm push
```
