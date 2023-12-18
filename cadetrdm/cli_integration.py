import shlex
import subprocess

import click

from .repositories import ProjectRepo, BaseRepo
from .initialize_repo import initialize_repo as initialize_git_repo_implementation, init_lfs
from .initialize_repo import clone as clone_implementation
from .conda_env_utils import prepare_conda_env as prepare_conda_env_implementation

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    pass


@cli.command()
@click.option('--path_to_repo', default=None,
              help='Path to folder for the repository. Optional.')
@click.argument('project_url')
def clone(project_url, path_to_repo: str = None):
    clone_implementation(project_url, path_to_repo)


@cli.command()
@click.option('--target_repo_location', default=None,
              help='Path to folder for the repository. Optional.')
@click.argument('source_repo_location')
@click.argument('source_repo_branch')
def import_remote_repo(source_repo_location, source_repo_branch, target_repo_location=None):
    repo = BaseRepo(".")
    repo.import_remote_repo(source_repo_location=source_repo_location,
                            source_repo_branch=source_repo_branch,
                            target_repo_location=target_repo_location)


@cli.command()
@click.argument('url')
@click.argument('namespace')
@click.argument('name')
def create_gitlab_remotes(url, namespace, name):
    repo = ProjectRepo(".")
    repo.create_gitlab_remotes(url=url, namespace=namespace, name=name)


@cli.command()
@click.argument('namespace')
@click.argument('name')
def create_github_remotes(namespace, name):
    repo = ProjectRepo(".")
    repo.create_github_remotes(namespace=namespace, name=name)

@cli.command()
def verify_unchanged_cache():
    repo = BaseRepo(".")
    repo.verify_unchanged_cache()


@cli.command()
@click.option('--re_load', default=False,
              help='Re-load all data.')
def fill_data_from_cadet_rdm_json(re_load=False):
    repo = BaseRepo(".")
    repo.fill_data_from_cadet_rdm_json(re_load=re_load)


@cli.command()
@click.argument('file_name')
@click.argument('results_commit_message')
def run_python_file(file_name, results_commit_message):
    repo = ProjectRepo(".")
    repo.enter_context()
    subprocess.run(["python", file_name])
    repo.exit_context(results_commit_message)


@cli.command()
@click.argument('command')
@click.argument('results_commit_message')
def run_command(command, results_commit_message):
    repo = ProjectRepo(".")
    repo.enter_context()
    subprocess.run(shlex.split(command))
    repo.exit_context(results_commit_message)


@cli.command()
@click.option('--output_repo_name', default="output",
              help='Name of the folder where the tracked output should be stored. Optional. Default: "output".')
@click.option('--gitignore', default=None,
              help='List of files to be added to the gitignore file. Optional.')
@click.option('--gitattributes', default=None,
              help='List of files to be added to the gitattributes file. Optional.')
@click.argument('path_to_repo')
def initialize_repo(path_to_repo: str, output_repo_name: (str | bool) = "output", gitignore: list = None,
                    gitattributes: list = None,
                    output_repo_kwargs: dict = None):
    initialize_git_repo_implementation(path_to_repo, output_repo_name, gitignore,
                                       gitattributes, output_repo_kwargs)


@cli.command()
@click.option("-p", '--path_to_repo', default=".",
              help='Path to repository to which the remote is added. Default is cwd.')
@click.argument('remote_url')
def add_remote_to_repo(remote_url: str, path_to_repo="."):
    repo = BaseRepo(path_to_repo)
    repo.add_remote(remote_url)
    print("Done.")


@cli.command()
@click.argument('file_type')
def add_filetype_to_lfs(file_type: str, ):
    repo = BaseRepo(".")
    repo.add_filetype_to_lfs(file_type)


@cli.command()
@click.option('--url', default=None,
              help='Url to the environment.yml file.')
def prepare_conda_env(url):
    prepare_conda_env_implementation(url)


@cli.command()
def print_output_log():
    # ToDo: test if Project or Output repo
    repo = ProjectRepo(".")
    repo.print_output_log()


@cli.command(help="Push all changes to the project and output repositories.")
def push():
    repo = ProjectRepo(".")
    repo.push(push_all=True)
