import click

from .repositories import ProjectRepo
from .initialize_repo import initialize_repo as initialize_git_repo_implementation, init_lfs
from .initialize_repo import initialize_from_remote as initialize_from_remote_implementation
from .conda_env_utils import prepare_conda_env as prepare_conda_env_implementation

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    pass


@cli.command()
@click.option('--path_to_repo', default=None,
              help='Path to folder for the repository. Optional.')
@click.argument('project_url')
def initialize_from_remote(project_url, path_to_repo: str = None):
    initialize_from_remote_implementation(project_url, path_to_repo)


@cli.command()
@click.option('--output_repo_name', default="output",
              help='Name of the folder where the tracked output should be stored. Optional. Default: "output".')
@click.option('--gitignore', default=None,
              help='List of files to be added to the gitignore file. Optional.')
@click.option('--gitattributes', default=None,
              help='List of files to be added to the gitattributes file. Optional.')
@click.option('--lfs_filetypes', default=None,
              help='List of filetypes to be handled by git lfs. Optional.')
@click.argument('path_to_repo')
def initialize_repo(path_to_repo: str, output_repo_name: (str | bool) = "output", gitignore: list = None,
                    gitattributes: list = None, lfs_filetypes: list = None,
                    output_repo_kwargs: dict = None):
    initialize_git_repo_implementation(path_to_repo, output_repo_name, gitignore,
                                       gitattributes, lfs_filetypes,
                                       output_repo_kwargs)


@cli.command()
@click.argument('path_to_repo')
@click.argument('remote_url')
def add_remote_to_repo(path_to_repo: str, remote_url: str, ):
    repo = ProjectRepo(path_to_repo)
    repo.add_remote(remote_url)
    print("Done.")


@cli.command()
@click.argument('path_to_repo')
@click.argument('file_type')
def add_file_type_to_lfs(path_to_repo: str, file_type: str, ):
    init_lfs(lfs_filetypes=[file_type], path=path_to_repo)
    repo = ProjectRepo(path_to_repo)
    repo.add_all_files()
    repo.commit(f"Add {file_type} to lfs")


@cli.command()
@click.option('--url', default=None,
              help='Url to the environment.yml file.')
def prepare_conda_env(url):
    prepare_conda_env_implementation(url)


@cli.command()
@click.argument('path_to_repo')
def print_output_log(path_to_repo):
    repo = ProjectRepo(path_to_repo)
    repo.print_output_log()
