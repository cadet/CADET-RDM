import os
import json
import uuid
from pathlib import Path

try:
    import git
except ImportError:
    # Adding this hint to save users the confusion of trying $pip install git
    raise ImportError("No module named git, please install the gitpython package")

import cadetrdm
from cadetrdm.repositories import ProjectRepo, OutputRepo
from cadetrdm.web_utils import ssh_url_to_http_url
from cadetrdm.io_utils import write_lines_to_file, is_tool, wait_for_user, init_lfs


def initialize_repo(path_to_repo: str, output_folder_name: (str | bool) = "output", gitignore: list = None,
                    gitattributes: list = None, output_repo_kwargs: dict = None):
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
    :return:
    """
    if not is_tool("git-lfs"):
        raise RuntimeError("Git LFS is not installed. Please install it via e.g. apt-get install git-lfs or the "
                           "instructions found below \n"
                           "https://docs.github.com/en/repositories/working-with-files"
                           "/managing-large-files/installing-git-large-file-storage")

    if gitignore is None:
        gitignore = get_default_gitignore() + ["*.ipynb"]

    gitignore.append(output_folder_name)
    gitignore.append(output_folder_name + "_cached")

    if gitattributes is None:
        gitattributes = []

    if output_repo_kwargs is None:
        output_repo_kwargs = {}

    starting_directory = os.getcwd()
    project_repo_uuid = str(uuid.uuid4())
    output_repo_uuid = str(uuid.uuid4())

    if path_to_repo != ".":
        os.makedirs(path_to_repo, exist_ok=True)
        os.chdir(path_to_repo)

    initialize_git()

    write_lines_to_file(path=".gitattributes", lines=gitattributes, open_type="a")
    write_lines_to_file(path=".gitignore", lines=gitignore, open_type="a")

    create_readme()
    create_environment_yml()

    ProjectRepo.add_jupytext_file()

    rdm_data = {
        "is_project_repo": True, "is_output_repo": False,
        "project_uuid": project_repo_uuid, "output_uuid": output_repo_uuid,
        "cadet_rdm_version": cadetrdm.__version__
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

    with open("output_remotes.json", "w") as file_handle:
        remotes_dict = {}
        json_dict = {"output_folder_name": output_folder_name, "output_remotes": remotes_dict}
        json.dump(json_dict, file_handle, indent=2)

    initialize_output_repo(output_folder_name, project_repo_uuid=project_repo_uuid,
                           output_repo_uuid=output_repo_uuid, **output_repo_kwargs)

    repo = ProjectRepo(".", output_folder=output_folder_name)
    repo.update_output_remotes_json()

    repo.commit("initial commit")

    os.chdir(starting_directory)


def initialize_git(folder="."):
    if folder != ":":
        starting_directory = os.getcwd()
        os.chdir(folder)

    try:
        repo = git.Repo(".")
        proceed = wait_for_user('The target directory already contains a git repo.\n'
                                'Please back up or push all changes to the repo before continuing.\n'
                                'Proceed?')
        if not proceed:
            raise KeyboardInterrupt
    except git.exc.InvalidGitRepositoryError:
        os.system(f"git init")

    if folder != ":":
        os.chdir(starting_directory)


def get_default_gitignore():
    return [".idea", "*diskcache*", "*tmp*", ".ipynb_checkpoints", "__pycache__"]


def get_default_lfs_filetypes():
    return ["*.jpg", "*.png", "*.xlsx", "*.h5", "*.ipynb", "*.pdf", "*.docx", "*.zip", "*.html"]


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
    :return:
    """
    starting_directory = os.getcwd()
    os.makedirs(output_folder_name, exist_ok=True)
    os.chdir(output_folder_name)

    if gitignore is None:
        gitignore = get_default_gitignore()

    if gitattributes is None:
        gitattributes = ["rdm-log.tsv merge=union"]

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
    file_lines = ["name: rdm_example", "channels:", "  - conda-forge", "dependencies:", "  - python=3.10", "  - conda",
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


def clone(project_url, path_to_repo: str = None):
    if path_to_repo is None:
        path_to_repo = project_url.split("/")[-1]
        path_to_repo = path_to_repo.replace(".git", "")
    print(f"Cloning {project_url} into {path_to_repo}")
    git.Repo.clone_from(project_url, path_to_repo)

    path_to_repo = Path(path_to_repo)

    # Clone output repo from remotes
    json_path = path_to_repo / "output_remotes.json"
    with open(json_path, "r") as file_handle:
        meta_dict = json.load(file_handle)

    output_folder_name = path_to_repo / meta_dict["output_folder_name"]
    ssh_remotes = list(meta_dict["output_remotes"].values())
    http_remotes = [ssh_url_to_http_url(url) for url in ssh_remotes]
    if len(ssh_remotes + http_remotes) == 0:
        raise RuntimeError("No output remotes configured in output_remotes.json")
    for output_remote in ssh_remotes + http_remotes:
        try:
            print(f"Attempting to clone {output_remote} into {output_folder_name}")
            git.Repo.clone_from(output_remote, output_folder_name)
        except Exception as e:
            print(e)
        else:
            break
    environment_path = Path(os.getcwd()) / path_to_repo / "environment.yml"

    repo = ProjectRepo(path_to_repo)
    repo.fill_data_from_cadet_rdm_json()

    print("To set up the project conda environment please run this command:\n"
          f"conda deactivate && conda env create -f '{environment_path}'")
