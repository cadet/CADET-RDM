import os
import json
from datetime import datetime
import random

try:
    import git
except ImportError:
    # Adding this hint to save users the confusion of trying $pip install git
    raise ImportError("No module named git, please install the gitpython package")


class GitRepo(git.Repo):
    def __init__(self, repository_path=None, output_folder=None, *args, **kwargs):

        """
        :param search_parent_directories:
            if True, all parent directories will be searched for a valid repo as well.

            Please note that this was the default behaviour in older versions of GitPython,
            which is considered a bug though.
        """

        if repository_path is None or repository_path == ".":
            repository_path = os.getcwd()
        super().__init__(repository_path, *args, **kwargs)

        self._most_recent_branch = "master"
        if output_folder is not False:
            if output_folder is not None:
                self._output_folder = output_folder
            elif output_folder is None:
                self._output_folder = "output"
                self._output_repo = GitRepo(os.path.join(self.working_dir, self._output_folder), output_folder=False)

    @property
    def output_repo(self):
        if self._output_repo is None:
            raise ValueError("The output repo has not been set yet.")
        return self._output_repo

    def set_output_repo(self, output_repo_folder_name):
        self._output_repo = GitRepo(os.path.join(self.working_dir, output_repo_folder_name), output_folder=False)
        self._output_folder = output_repo_folder_name

    def add_all_files(self, automatically_add_new_files=True):
        if len(self.untracked_files) > 0:
            untracked_files = "\n".join(["- " + file for file in self.untracked_files])

        if automatically_add_new_files:
            for f in self.untracked_files:
                self.git.add(f)
        else:
            proceed = input(
                f'Found untracked files. Adding the following untracked files to git: \n{untracked_files}\n'
                f'Proceed? Y/n \n'
            )
            if proceed.lower() == "y" or proceed == "":
                for f in self.untracked_files:
                    self.git.add(f)
            else:
                raise KeyboardInterrupt

        changed_files = self.changed_files
        for f in changed_files:
            self.git.add(f)
        return self.untracked_files + changed_files

    @property
    def changed_files(self):
        changed_files = self.git.diff(None, name_only=True).split('\n')
        if "" in changed_files:
            changed_files.remove("")
        return changed_files

    def exist_unstaged_changes(self):
        return len(self.untracked_files) > 0 or len(self.changed_files) > 0

    def update_package_list(self):
        repo_path = self.working_dir
        print("Dumping conda environment.yml, this might take a moment.")
        os.system(f"conda env export > {repo_path}/conda_environment.yml")
        print("Dumping conda independent environment.yml, this might take a moment.")
        os.system(f"conda env export --from-history > {repo_path}/conda_independent_environment.yml")
        print("Dumping pip requirements.txt.")
        os.system(f"pip freeze > {repo_path}/pip_requirements.txt")
        print("Dumping pip independent requirements.txt.")
        os.system(f"pip list --not-required --format freeze > {repo_path}/pip_independent_requirements.txt")

    def full_commit(self, message: str, add_all=True, update_packages=True):
        if update_packages:
            self.update_package_list()
        if add_all:
            self.add_all_files()
        commit_return = self.git.commit("-m", message)
        print("\n" + commit_return)

    def git_ammend(self, ):
        self.git.commit("--amend", "--no-edit")

    def print_status(self):
        print(self.git.status())

    def print_log(self):
        print(self.git.log())

    def commit_results(self):
        if self.exist_unstaged_changes():
            print("Found uncommitted changes in the project repository.\nAborting results commit.")
            return

        """Get new branch name"""
        project_repo_hash = str(self.head.commit)
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")[:-4]
        branch_name = "_".join([str(self.active_branch), project_repo_hash[:7], self._output_folder, timestamp])

        """ Git shenanigans"""
        *_, earliest_commit = self._output_repo.iter_commits()

        self._output_repo.git.add(".")
        self._output_repo.git.stash()  # equivalent to $ git stash
        self._output_repo.git.checkout('-b', branch_name)  # equivalent to $ git checkout -b %branch_name
        self._output_repo.git.reset('--hard', earliest_commit)  # equivalent to $ git reset --hard %commit_hash

        try:
            self._output_repo.git.stash('pop')  # equivalent to $ git stash pop
        except git.exc.GitCommandError as e:
            # Will raise error because the stash cannot be applied without conflicts. This is expected and fine
            if 'CONFLICT (modify/delete)' in e.stdout:
                pass
            else:
                raise e

        """ Actual Git commit """

        # self._output_repo.add_all_files()
        self._output_repo.git.add(".")
        self._output_repo.git.commit("-m", "add more data")

        """ Update logs in master branch"""
        output_repo_hash = str(self._output_repo.head.commit)

        self._output_repo.git.checkout("master")

        json_filepath = os.path.join(self.working_dir, self._output_folder, f"{branch_name}.json")
        # note: if filename of "log.csv" is changed, this also has to be changed in the gitattributes of the init repo func
        csv_filepath = os.path.join(self.working_dir, self._output_folder, "log.csv")

        meta_info_dict = {"Output repo branch": branch_name,
                          "Output repo commit hash": output_repo_hash,
                          "Project repo commit hash": project_repo_hash,
                          "Project repo folder name": os.path.split(self.working_dir)[-1],
                          "Project repo remotes": self.remotes,
                          }
        csv_header = ",".join(meta_info_dict.keys())
        csv_data = ",".join([str(x) for x in meta_info_dict.values()])

        with open(json_filepath, "w") as f:
            json.dump(meta_info_dict, f, indent=2)

        if not os.path.exists(csv_filepath):
            with open(csv_filepath, "w") as f:
                f.write(csv_header + "\n")
                # csv.writer(csv_header + "\n")

        with open(csv_filepath, "r") as f:
            existing_header = f.readline().replace("\n", "")
            if existing_header != csv_header:
                raise ValueError("The used structure of the meta_dict doesn't match the header found in log.csv")

        with open(csv_filepath, "a") as f:
            f.write(csv_data + "\n")

        self._output_repo.git.add(".")
        self._output_repo.git.commit("-m", branch_name)

        self._output_repo.git.checkout(branch_name)
        self._most_recent_branch = branch_name

    def check_results_master(self):
        self._most_recent_branch = self._output_repo.active_branch.name
        self._output_repo.git.checkout("master")

    def reload_recent_results(self):
        self._output_repo.git.checkout(self._most_recent_branch)


def add_linebreaks(input_list):
    return [line + "\n" for line in input_list]


def init_lfs(lfs_filetypes):
    os.system(f"git lfs install")
    lfs_filetypes_string = " ".join(["'" + file + "'" for file in lfs_filetypes])
    os.system(f"git lfs track {lfs_filetypes_string}")


def write_lines_to_file(path, lines):
    with open(path, "a") as f:
        f.writelines(add_linebreaks(lines))


def is_tool(name):
    """Check whether `name` is on PATH and marked as executable."""

    from shutil import which

    return which(name) is not None


def initialize_git_repo(path_to_repo, output_repo_name="output", gitignore: list = None,
                        gitattributes: list = None, lfs_filetypes: list = None,
                        output_repo_kwargs: dict = None):
    if not is_tool("git-lfs"):
        raise RuntimeError("Git LFS is not installed. Please install it via e.g. apt-get install git-lfs or the "
                           "instructions found below \n"
                           "https://docs.github.com/en/repositories/working-with-files"
                           "/managing-large-files/installing-git-large-file-storage")

    if gitignore is None:
        gitignore = [".idea", "*diskcache*", "*tmp*", ".ipynb_checkpoints", "__pycache__"]
    if output_repo_name is not None:
        gitignore.append(output_repo_name)
    if gitattributes is None:
        gitattributes = []
    if lfs_filetypes is None:
        lfs_filetypes = ["*.jpg", "*.png", "*.xlsx", "*.m5", "*.ipynb"]
    starting_directory = os.getcwd()

    if path_to_repo != ".":
        if os.path.exists(path_to_repo) and len(os.listdir(path_to_repo)) > 0:
            raise ValueError("Path to repository already exists and is not an empty directory.")
        os.makedirs(path_to_repo)
        os.chdir(path_to_repo)

    os.system(f"git init")

    init_lfs(lfs_filetypes)

    write_lines_to_file(path=".gitattributes", lines=gitattributes)
    write_lines_to_file(path=".gitignore", lines=gitignore)

    if output_repo_kwargs is None:
        output_repo_kwargs = {"gitattributes": ["log.csv merge=union"]}
    if output_repo_name is not None:
        initialize_git_repo(output_repo_name, output_repo_name=None, **output_repo_kwargs)
        repo = GitRepo(".")
    else:
        repo = GitRepo(".", output_folder=False)

    repo.git.add(".")
    repo.git.commit("-m", "initial commit")

    os.chdir(starting_directory)
    return


def example_generate_results_data(seed=None):
    import matplotlib.pyplot as plt
    import numpy as np

    if seed is not None:
        np.random.seed(seed)

    plt.figure()
    plt.scatter(np.arange(0, 50), np.random.random(50), alpha=0.5)
    plt.scatter(np.arange(0, 50), np.random.random(50), alpha=0.5)
    plt.scatter(np.arange(0, 50), np.random.random(50), alpha=0.5)
    plt.savefig(os.path.join("output", "fig.png"))
    plt.savefig(os.path.join("output", "fig.jpg"), dpi=1200)
    plt.savefig(os.path.join("output", f"fig_{np.random.randint(265)}.png"))


def example_usage():
    home_dir = os.path.expanduser("~")
    os.chdir(home_dir)

    if not os.path.exists("ModSimData"):
        initialize_git_repo("ModSimData")

    os.chdir('ModSimData')

    project_repo = GitRepo(".")

    # Add changes to the project code
    random_number = random.randint(0, 265)
    with open("random_number.txt", "a") as file:
        file.write(str(random_number))

    # Generate data
    example_generate_results_data(seed=random_number)

    # Try to commit results with uncommitted changes in the project repo and see it will fail.
    project_repo.commit_results()

    # commit changes to project code
    project_repo.full_commit(message="Update code", update_packages=True)

    # Now successfully commit changes to results
    project_repo.commit_results()

    # Check out logs in master branch
    project_repo.check_results_master()

    # Go back to data
    project_repo.reload_recent_results()
