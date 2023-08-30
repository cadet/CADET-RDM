import os

import click

from cadetrdm.repositories import ProjectRepo, ResultsRepo


def add_linebreaks(input_list):
    """
    Add linebreaks between each entry in the input_list
    """
    return [line + "\n" for line in input_list]


def init_lfs(lfs_filetypes: list, path: str = None):
    """
    Initialize lfs in the git repository at the path.
    If path is None, the current working directory is used.
    :param lfs_filetypes:
        List of file types to be handled by lfs.
        Format should be e.g. ["*.jpg", "*.png"] for jpg and png files.
    """
    if path is not None:
        previous_path = os.getcwd()
        os.chdir(path)

    os.system(f"git lfs install")
    lfs_filetypes_string = " ".join(lfs_filetypes)
    os.system(f"git lfs track {lfs_filetypes_string}")

    if path is not None:
        os.chdir(previous_path)


def write_lines_to_file(path, lines, open_type="a"):
    """
    Convenience function. Write lines to a file at path with added newlines between each line.
    :param path:
        Path to file.
    :param lines:
        List of lines to be written to file.
    :param open_type:
        The way the file should be opened. I.e. "a" for append and "w" for fresh write.
    """
    with open(path, open_type) as f:
        f.writelines(add_linebreaks(lines))


def is_tool(name):
    """Check whether `name` is on PATH and marked as executable."""

    from shutil import which
    return which(name) is not None


@click.command()
@click.option('--output_repo_name', default="output",
              help='Name of the folder where the tracked output should be stored. Optional. Default: "output".')
@click.option('--gitignore', default=None,
              help='List of files to be added to the gitignore file. Optional.')
@click.option('--gitattributes', default=None,
              help='List of files to be added to the gitattributes file. Optional.')
@click.option('--lfs_filetypes', default=None,
              help='List of filetypes to be handled by git lfs. Optional.')
@click.argument('path_to_repo')
def initialize_git_repo_cli(path_to_repo: str, output_repo_name: (str | bool) = "output", gitignore: list = None,
                            gitattributes: list = None, lfs_filetypes: list = None,
                            output_repo_kwargs: dict = None):
    initialize_git_repo(path_to_repo, output_repo_name, gitignore,
                        gitattributes, lfs_filetypes,
                        output_repo_kwargs)


def initialize_git_repo(path_to_repo: str, output_repo_name: (str | bool) = "output", gitignore: list = None,
                        gitattributes: list = None, lfs_filetypes: list = None,
                        output_repo_kwargs: dict = None):
    """
    Initialize a git repository at the given path with an optional included output results repository.

    :param path_to_repo:
        Path to main repository.
    :param output_repo_name:
        Name for the output repository.
    :param gitignore:
        List of files to be added to the gitignore file.
    :param gitattributes:
        List of lines to be added to the gittatributes file
    :param lfs_filetypes:
        List of filetypes to be handled by git lfs.
    :param output_repo_kwargs:
        kwargs to be given to the creation of the output repo initalization function.
        Include gitignore, gitattributes, and lfs_filetypes kwargs.
    :return:
    """
    if not is_tool("git-lfs"):
        raise RuntimeError("Git LFS is not installed. Please install it via e.g. apt-get install git-lfs or the "
                           "instructions found below \n"
                           "https://docs.github.com/en/repositories/working-with-files"
                           "/managing-large-files/installing-git-large-file-storage")

    if gitignore is None:
        gitignore = [".idea", "*diskcache*", "*tmp*", ".ipynb_checkpoints", "__pycache__"]

    if output_repo_name:
        gitignore.append(output_repo_name)
        gitignore.append(output_repo_name + "_cached")

    if gitattributes is None:
        gitattributes = []

    if lfs_filetypes is None:
        lfs_filetypes = ["*.jpg", "*.png", "*.xlsx", "*.h5", "*.ipynb", "*.pdf", ".docx"]

    starting_directory = os.getcwd()

    if path_to_repo != ".":
        if os.path.exists(path_to_repo) and len(os.listdir(path_to_repo)) > 0:
            raise ValueError("Path to repository already exists and is not an empty directory.")
        os.makedirs(path_to_repo, exist_ok=True)
        os.chdir(path_to_repo)

    os.system(f"git init")

    init_lfs(lfs_filetypes)

    write_lines_to_file(path=".gitattributes", lines=gitattributes)
    write_lines_to_file(path=".gitignore", lines=gitignore)

    if output_repo_kwargs is None:
        output_repo_kwargs = {"gitattributes": ["logs/log.csv merge=union"]}

    if output_repo_name:
        # This means we are in the project repo and should now initialize the output_repo
        initialize_git_repo(output_repo_name, output_repo_name=False, **output_repo_kwargs)
        # This instance of ProjectRepo is therefore the project repo
        repo = ProjectRepo(".", output_folder=output_repo_name)
    else:
        # If output_repo_name is False we are in the output_repo and should finish by committing the changes
        repo = ResultsRepo(".")

    repo.commit("initial commit")

    os.chdir(starting_directory)
