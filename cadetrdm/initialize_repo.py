import json
import os
import shutil
import uuid
from pathlib import Path
from typing import List

from cookiecutter.main import cookiecutter

try:
    import git
except ImportError:
    # Adding this hint to save users the confusion of trying $pip install git
    raise ImportError("No module named git, please install the gitpython package")

import cadetrdm
from cadetrdm.repositories import ProjectRepo, OutputRepo
from cadetrdm.io_utils import write_lines_to_file, wait_for_user, init_lfs, test_for_lfs
import cadetrdm.templates.dockerfile_template as dockerfile_template

def initialize_repo(path_to_repo: str | Path, output_folder_name: (str | bool) = "output", gitignore: list = None,
                    gitattributes: list = None, output_repo_kwargs: dict = None, cookiecutter_template: str = None):
    """
    Initialize a git repository at the given path with an optional included output results repository.

    :param path_to_repo:
        Path to main repository.
    :param output_folder_name:
        Name for the output repository.
    :param gitignore:
        List of files to be added to the gitignore file.
    :param gitattributes:
        List of lines to be added to the gitattributes file
    :param output_repo_kwargs:
        kwargs to be given to the creation of the output repo initalization function.
        Include gitignore, gitattributes, and lfs_filetypes kwargs.
    """
    test_for_lfs()

    if cookiecutter_template is not None:
        init_cookiecutter(cookiecutter_template, path_to_repo)

    if gitignore is None:
        gitignore = get_default_gitignore() + ["*.ipynb", "*.h5"]

    gitignore.append(f"/{output_folder_name}/")
    gitignore.append(f"/{output_folder_name}_cached/")

    if gitattributes is not None:
        write_lines_to_file(path=".gitattributes", lines=gitattributes, open_type="a")

    if output_repo_kwargs is None:
        output_repo_kwargs = {}

    starting_directory = os.getcwd()
    project_repo_uuid = str(uuid.uuid4())
    output_repo_uuid = str(uuid.uuid4())

    if path_to_repo != ".":
        os.makedirs(path_to_repo, exist_ok=True)
        os.chdir(path_to_repo)

    initialize_git()

    write_lines_to_file(path=".gitignore", lines=gitignore, open_type="a")

    create_readme()
    create_environment_yml()
    create_dockerfile()

    ProjectRepo._add_jupytext_file()

    rdm_data = {
        "is_project_repo": True, "is_output_repo": False,
        "project_uuid": project_repo_uuid, "output_uuid": output_repo_uuid,
        "cadet_rdm_version": cadetrdm.__version__,
        "output_remotes": {"output_folder_name": output_folder_name, "output_remotes": {}}
    }
    with open(".cadet-rdm-data.json", "w") as f:
        json.dump(rdm_data, f, indent=2)

    with open(".cadet-rdm-cache.json", "w") as f:
        json.dump({"__example/path/to/repo__": {
            "source_repo_location": "git@jugit.fz-juelich.de:IBG-1/ModSim/cadet"
                                    "/agile_cadet_rdm_presentation_output.git",
            "branch_name": "output_from_master_3910c84_2023-10-25_00-17-23",
            "commit_hash": "6e3c26527999036e9490d2d86251258fe81d46dc"
        }}, f, indent=2)

    initialize_output_repo(output_folder_name, project_repo_uuid=project_repo_uuid,
                           output_repo_uuid=output_repo_uuid, **output_repo_kwargs)

    repo = ProjectRepo(".")
    repo.update_output_remotes_json()

    files = [".gitignore",
             "README.md",
             ".cadet-rdm-cache.json",
             ".cadet-rdm-data.json",
             "environment.yml",
             "jupytext.yml",
             "Dockerfile",
             ]
    if gitattributes is not None:
        files.append(".gitattributes")

    for file in files:
        repo._git.add(file)

    repo.commit("initial CADET RDM commit", add_all=False)

    os.chdir(starting_directory)
    del repo


def init_cookiecutter(cookiecutter_template, path_to_repo):
    """
    Initialize from cookiecutter template. Because cookiecutter can only create the files in a sub-directory
    but cadet-rdm init can be called from within a folder with "path_to_repo" == ".", we copy the files from the
    generated_dir folder into the path_to_repo folder afterwards.

    :param cookiecutter_template:
    :param path_to_repo:
    """
    generated_dir = cookiecutter(cookiecutter_template, output_dir=path_to_repo)
    file_names = os.listdir(generated_dir)
    for file_name in file_names:
        shutil.move(os.path.join(generated_dir, file_name), path_to_repo)
    shutil.rmtree(generated_dir)


# def re_initialize_existing_repo(path_to_repo: str | Path, **output_repo_kwargs):
#     path_to_repo = "."
#     output_repo_kwargs = {}
#
#     starting_directory = os.getcwd()
#     os.chdir(path_to_repo)
#
#     repo = ProjectRepo(".")
#
#     if Path(repo._output_folder).exists():
#         raise RuntimeError(f"Output repo at {repo._output_folder} already exists.")
#
#     initialize_output_repo(repo._output_folder, project_repo_uuid=repo._project_uuid,
#                            output_repo_uuid=repo._output_uuid, **output_repo_kwargs)
#
#     os.chdir(starting_directory)


def initialize_git(folder="."):
    starting_directory = os.getcwd()
    if folder != ":":
        os.chdir(folder)

    try:
        repo = git.Repo(".")
        proceed = wait_for_user('The target directory already contains a git repo.\n'
                                'Please commit or stash all changes to the repo before continuing.\n'
                                'Proceed?')
        if not proceed:
            raise KeyboardInterrupt
    except git.exc.InvalidGitRepositoryError:
        os.system(f"git init -b main")

    if folder != ":":
        os.chdir(starting_directory)


def get_default_gitignore():
    return [".idea", "*diskcache*", "*tmp*", ".ipynb_checkpoints", "__pycache__"]


def get_default_lfs_filetypes():
    return ["*.jpg", "*.png", "*.xlsx", "*.h5", "*.ipynb", "*.pdf", "*.docx", "*.zip", "*.html", "*.csv"]


def initialize_output_repo(output_folder_name, gitignore: list = None,
                           gitattributes: list = None, lfs_filetypes: list = None,
                           project_repo_uuid: str = None, output_repo_uuid: str = None):
    """
    Initialize a git repository at the given path with an optional included output results repository.

    :param output_folder_name:
        Name for the output repository.
    :param gitignore:
        List of files to be added to the gitignore file.
    :param gitattributes:
        List of lines to be added to the gitattributes file
    :param lfs_filetypes:
        List of filetypes to be handled by git lfs.
    """
    starting_directory = os.getcwd()
    os.makedirs(output_folder_name, exist_ok=True)
    os.chdir(output_folder_name)

    if gitignore is None:
        gitignore = get_default_gitignore()

    if gitattributes is None:
        gitattributes = ["log.tsv merge=union"]

    if lfs_filetypes is None:
        lfs_filetypes = get_default_lfs_filetypes()

    initialize_git()

    write_lines_to_file(path=".gitattributes", lines=gitattributes, open_type="a")
    write_lines_to_file(path=".gitignore", lines=gitignore, open_type="a")

    rdm_data = {
        "is_project_repo": False, "is_output_repo": True,
        "project_uuid": project_repo_uuid, "output_uuid": output_repo_uuid,
        "cadet_rdm_version": cadetrdm.__version__
    }
    with open(".cadet-rdm-data.json", "w") as f:
        json.dump(rdm_data, f, indent=2)

    init_lfs(lfs_filetypes)

    create_output_readme()

    repo = OutputRepo(".")
    repo.commit("initial commit")

    os.chdir(starting_directory)


def create_environment_yml():
    file_lines = ["name: rdm_example", "channels:", "  - conda-forge", "dependencies:", "  - python=3.10",
                  "  - cadet", "  - pip", "  - pip:", "      - cadet-process", "      - cadet-rdm"]
    if not os.path.exists("environment.yml"):
        write_lines_to_file("environment.yml", file_lines, open_type="w")


def create_readme():
    readme_lines = ["# Project repo", "Your code goes in this repo.", "Please add a description here including: ",
                    "- authors", "- project", "- things we will find interesting later", "", "",
                    "Please update the environment.yml with your python environment requirements.", "", "",
                    "The output repository can be found at:",
                    "[output_repo]() (not actually set yet because no remote has been configured at this moment"]
    write_lines_to_file("README.md", readme_lines, open_type="a")


def create_output_readme():
    readme_lines = ["# Output repo", "Your results will be stored here.", "Please add a description here including: ",
                    "- authors", "- project", "- things we will find interesting later", "", "",
                    "The project repository can be found at:",
                    "[project_repo]() (not actually set yet because no remote has been configured at this moment"]
    write_lines_to_file("README.md", readme_lines, open_type="a")


def create_dockerfile():
    write_lines_to_file("Dockerfile", dockerfile_template, open_type="w")

