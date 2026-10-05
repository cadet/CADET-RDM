import subprocess
from pathlib import Path
import shlex
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from cadetrdm.repositories import ProjectRepo

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def cli() -> None:
    """CADET-RDM command line interface."""
    pass


@cli.command(help="Create an empty CADET-RDM repository or initialize over an existing git repo.")
@click.option('--output_directory_name', default="output",
              help='Name of the directory where the tracked output should be stored. '
                   'Optional. Default: "output".')
@click.option('--gitignore', default=None,
              help='List of files to be added to the gitignore file. Optional.')
@click.option('--gitattributes', default=None,
              help='List of files to be added to the gitattributes file. Optional.')
@click.option('--cookiecutter', default=None,
              help='URL or path to cookiecutter template. Optional.')
@click.argument('path_to_repo', required=False)
def init(
    path_to_repo: str | None = None,
    output_directory_name: str | bool = "output",
    gitignore: list | None = None,
    gitattributes: list | None = None,
    cookiecutter: str | None = None,
    output_repo_kwargs: dict | None = None,
) -> None:
    """Create an empty CADET-RDM repository or initialize over an existing git repo."""
    if path_to_repo is None:
        path_to_repo = "."
    from cadetrdm.initialize_repo import initialize_repo as initialize_git_repo_implementation
    initialize_git_repo_implementation(path_to_repo, output_directory_name, gitignore,
                                       gitattributes, output_repo_kwargs, cookiecutter)


@cli.command(help="Clone a repository into a new empty directory.")
@click.argument('project_url')
@click.argument('directory', required=False)
def clone(project_url: str, directory: str | None = None) -> None:
    """Clone a repository into a new empty directory."""
    from cadetrdm import ProjectRepo
    repo = ProjectRepo.clone(url=project_url, to_path=directory)
    del repo


@cli.command(name="log", help="Show commit logs.")
def print_log() -> None:
    """Show commit logs."""
    from cadetrdm.repositories import BaseRepo

    repo = BaseRepo(".")
    repo.print_log()
    del repo


@cli.command(name="check", help="Ensure metadata is consistent.")
def check() -> None:
    """Ensure metadata is consistent."""
    repo = get_project_repo()
    repo.check()
    del repo


@cli.command(help="Push all changes to the project and output repositories.")
@click.option('--single', "-s", is_flag=True, help="Push only changes of the current branch.")
def push(single: bool = False) -> None:
    """Push all changes to the project and output repositories."""
    repo = get_project_repo()
    repo.push(push_all=not single)
    del repo


def get_project_repo(path: str = ".") -> "ProjectRepo":
    """
    Get the project repo to a given path.

    If the path is an output repository, the project repository containing it is returned.

    Parameters
    ----------
    path : str, optional
        Path to a project or output repository.

    Returns
    -------
    ProjectRepo
        The project repository.
    """
    from cadetrdm.repositories import ProjectRepo, BaseRepo
    base_repo = BaseRepo(path)
    if base_repo._metadata["is_project_repo"]:
        repo = ProjectRepo(path)
    elif base_repo._metadata["is_output_repo"]:
        repo = ProjectRepo(Path(path).parent)
    else:
        raise ValueError("Current directory is neither Project nor Output repository")
    return repo


@cli.command(help="Record changes to the repository")
@click.option("--message", "-m", help="commit message")
@click.option("--all", "-a", is_flag=True, help="commit all changed files")
def commit(message: str, all: bool) -> None:
    """Record changes to the repository."""
    from cadetrdm.repositories import ProjectRepo
    repo = ProjectRepo(".")
    repo.commit(message, all)
    del repo


@cli.command(help="Stage changes")
@click.argument("filepath", type=click.Path())
def add(filepath: str) -> None:
    """Stage changes."""
    from cadetrdm.repositories import ProjectRepo
    repo = ProjectRepo(".")
    repo.add(filepath)


@cli.group(help="Execute commands and track the results.")
def run() -> None:
    """Execute commands and track the results."""
    pass


@run.command(name="python")
@click.argument('file_name')
@click.argument('results_commit_message')
def run_python_file(file_name: str, results_commit_message: str) -> None:
    """Run a python file and commit its results."""
    from cadetrdm.repositories import ProjectRepo
    repo = ProjectRepo(".")
    repo.enter_context()
    subprocess.run(["python", file_name])
    repo.exit_context(results_commit_message, {"command": f"python {file_name}"})
    del repo


@run.command(name="command")
@click.argument('command', nargs=-1)
@click.argument('results_commit_message')
def run_command(command: tuple[str, ...] | str, results_commit_message: str) -> None:
    """Run a shell command and commit its results."""
    from cadetrdm.repositories import ProjectRepo
    repo = ProjectRepo(".")
    repo.enter_context(force=True)
    if isinstance(command, tuple):
        command = " && ".join(command)
    command = shlex.split(command)
    results = subprocess.run(command, text=True, shell=False, capture_output=True)
    print(f"Command completed with stdout: {results.stdout} \nand stderr: {results.stderr}")
    repo.exit_context(results_commit_message, {"command": command})
    del repo


@cli.group(help="Create, add, and manage remotes.")
def remote() -> None:
    """Create, add, and manage remotes."""
    pass


@remote.command(name="add", help="Add a remote to the repository.")
@click.option('--name', '-n', default=None)
@click.argument('remote_url')
def add_remote(name: str | None = None, remote_url: str | None = None) -> None:
    """Add a remote to the repository."""
    from cadetrdm.repositories import BaseRepo
    repo = BaseRepo(".")
    repo.add_remote(remote_url=remote_url, remote_name=name)
    print("Done.")
    del repo


@remote.command(name="set-url", help="Set the URL of a remote.")
@click.argument('name')
@click.argument('remote_url')
def set_url(name: str, remote_url: str) -> None:
    """Set the url of a remote and commit the changed metadata."""
    from cadetrdm.repositories import BaseRepo
    repo = BaseRepo(".")
    repo.remote_set_url(url=remote_url, name=name)
    print(f"Set url of remote {name} to {remote_url}. Commiting changes to metadata.")
    project_repo = get_project_repo()
    project_repo.check(commit=True)
    del repo, project_repo


@remote.command(name="create")
@click.argument('url')
@click.argument('namespace')
@click.argument('name')
@click.argument('username', required=False)
@click.argument('push', required=False)
def create_remotes(
    url: str,
    namespace: str,
    name: str,
    username: str | None = None,
    push: bool = True,
) -> None:
    """Create remotes for the project and output repositories."""
    if username is None:
        username = namespace

    from cadetrdm.repositories import ProjectRepo
    repo = ProjectRepo(".")
    repo.create_remotes(name=name, namespace=namespace, url=url, username=username, push=push)
    del repo


@remote.command(name="list")
def list_remotes() -> None:
    """List the remotes of the repository."""
    from cadetrdm.repositories import BaseRepo
    repo = BaseRepo(".")
    for _remote, url in zip(repo.remotes, repo.remote_urls):
        print(_remote, ": ", url)
    del repo


@cli.group(help="Manage large file storage settings.")
def lfs() -> None:
    """Manage large file storage settings."""
    pass


@lfs.command(name="add", help="Add a filetype to git lfs.")
@click.argument('file_types', nargs=-1)
def add_filetype_to_lfs(file_types: tuple[str, ...]) -> None:
    """Add a filetype to git lfs."""
    from cadetrdm.repositories import OutputRepo
    repo = OutputRepo(".")
    for f_type in file_types:
        repo.add_filetype_to_lfs(f_type)
    del repo


@cli.group(help="Manage data and input-data-repositories.")
def data() -> None:
    """Manage data and input-data-repositories."""
    pass


@data.command(
    name="import",
    help="Import static data into the output repository without commiting the project status.",
)
@click.argument('source_path')
@click.argument('commit_message')
def import_static_data(source_path: str, commit_message: str) -> None:
    """Import static data into the output repository."""
    from cadetrdm.repositories import ProjectRepo
    repo = ProjectRepo(".")
    repo.import_static_data(
        source_path=source_path,
        commit_message=commit_message,
    )
    del repo


@data.command(name="clone", help="Import a remote repository into a given location.")
@click.argument('source_repo_location')
@click.argument('source_repo_branch')
@click.argument('target_repo_location', required=False)
def import_remote_repo(
    source_repo_location: str,
    source_repo_branch: str,
    target_repo_location: str | None = None,
) -> None:
    """Import a remote repository into a given location."""
    from cadetrdm.repositories import BaseRepo
    repo = BaseRepo(".")
    repo.import_remote_repo(source_repo_location=source_repo_location,
                            source_repo_branch=source_repo_branch,
                            target_repo_location=target_repo_location)
    del repo


@data.command(name="fetch", help="Fill data cache based on cadet-rdm.json.")
@click.option('--re_load', is_flag=True,
              help='Re-load all data.')
def fill_data_from_cadet_rdm_json(re_load: bool = False) -> None:
    """Fill data cache based on cadet-rdm.json."""
    from cadetrdm.repositories import ProjectRepo
    repo = ProjectRepo(".")
    repo.fill_data_from_cadet_rdm_json(re_load=re_load)
    del repo


@data.command(name="cache", help="Copy data from the output repo to the cache.")
@click.argument("branch")
def copy_to_cache(branch: str) -> None:
    """Copy data from the output repo to the cache."""
    from cadetrdm.repositories import ProjectRepo
    repo = ProjectRepo(".")
    repo.copy_data_to_cache(branch)
    del repo


@data.command(name="verify", help="Verify that cache is unchanged.")
def verify_unchanged_cache() -> None:
    """Verify that cache is unchanged."""
    from cadetrdm.repositories import BaseRepo
    repo = BaseRepo(".")
    repo.verify_unchanged_cache()
    del repo


@data.command(name="log", help="Print data logs.")
def print_data_log() -> None:
    """Print data logs."""
    from cadetrdm.repositories import ProjectRepo, BaseRepo, OutputRepo
    import json

    repo = BaseRepo(".")

    with open(repo.data_json_path, "r", encoding="utf-8") as handle:
        rdm_data = json.load(handle)
    if rdm_data["is_project_repo"]:
        repo = ProjectRepo(".")
        repo.print_output_log()
    else:
        repo = OutputRepo()
        repo.print_output_log()
    del repo
