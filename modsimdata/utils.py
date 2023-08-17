import os
import json
from datetime import datetime
import random
import shutil
import contextlib

try:
    import git
except ImportError:
    # Adding this hint to save users the confusion of trying $pip install git
    raise ImportError("No module named git, please install the gitpython package")


class BaseRepo(git.Repo):
    def __init__(self, repository_path=None, search_parent_directories=False, *args, **kwargs):
        """
        from git.Repo:
        :param search_parent_directories:
            if True, all parent directories will be searched for a valid repo as well.

            Please note that this was the default behaviour in older versions of GitPython,
            which is considered a bug though.
        """

        if repository_path is None or repository_path == ".":
            repository_path = os.getcwd()
        super().__init__(repository_path, search_parent_directories=search_parent_directories, *args, **kwargs)

        self._most_recent_branch = self.active_branch.name
        self._earliest_commit = None

    @property
    def earliest_commit(self):
        if self._earliest_commit is None:
            *_, earliest_commit = self.iter_commits()
            self._earliest_commit = earliest_commit

        return self._earliest_commit

    def delete_active_branch(self):
        previous_branch = self.active_branch.name
        if str(self.head.commit) == self.earliest_commit:
            self.git.checkout("master")
            self.git.branch("-d", previous_branch)

    def add_all_files(self, automatically_add_new_files=True):
        untracked_files = ""
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

    @property
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
        if not self.exist_unstaged_changes:
            print(f"No changes to commit in repo {self.working_dir}")
            return

        print(f"Commiting changes to repo {self.working_dir}")
        if update_packages:
            self.update_package_list()
        if add_all:
            self.add_all_files()
        commit_return = self.git.commit("-m", message)
        print("\n" + commit_return + "\n")

    def git_ammend(self, ):
        self.git.commit("--amend", "--no-edit")

    def print_status(self):
        print(self.git.status())

    def print_log(self):
        print(self.git.log())

    def stash_all_changes(self):
        if not self.exist_unstaged_changes:
            raise RuntimeError("No changes in repo to stash.")
        self.git.add(".")
        self.git.stash()

    def prepare_new_branch(self, branch_name):
        self.git.checkout('-b', branch_name)  # equivalent to $ git checkout -b %branch_name
        self.git.reset('--hard', self.earliest_commit)  # equivalent to $ git reset --hard %commit_hash

    def apply_stashed_changes(self):
        try:
            self.git.stash('pop')  # equivalent to $ git stash pop
        except git.exc.GitCommandError as e:
            # Will raise error because the stash cannot be applied without conflicts. This is expected
            if 'CONFLICT (modify/delete)' in e.stdout:
                pass
            else:
                raise e

    def test_for_uncommitted_changes(self):
        if self.exist_unstaged_changes:
            raise RuntimeError(f"Found uncommitted changes in the repository {self.working_dir}.")


class ProjectRepo(BaseRepo):
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

        if output_folder is not None:
            self._output_folder = output_folder
        elif output_folder is None:
            self._output_folder = "output"

        self._output_repo = ResultsRepo(os.path.join(self.working_dir, self._output_folder))

    @property
    def output_repo(self):
        if self._output_repo is None:
            raise ValueError("The output repo has not been set yet.")
        return self._output_repo

    def set_output_repo(self, output_repo_folder_name):
        self._output_repo = ProjectRepo(os.path.join(self.working_dir, output_repo_folder_name), output_folder=False)
        self._output_folder = output_repo_folder_name

    def get_new_output_branch_name(self):
        """Get new branch name"""
        project_repo_hash = str(self.head.commit)
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")[:-4]
        branch_name = "_".join([str(self.active_branch), project_repo_hash[:7], self._output_folder, timestamp])
        return branch_name

    def commit_results(self, message):
        self.test_for_uncommitted_changes()

        self.output_repo.stash_all_changes()

        new_branch_name = self.get_new_output_branch_name()
        self.output_repo.prepare_new_branch(new_branch_name)

        self.output_repo.apply_stashed_changes()

        """ Actual Git commit """
        self._output_repo.git.add(".")
        self._output_repo.git.commit("-m", message)

        self.update_output_master_logs()

    def check_results_master(self):
        self._most_recent_branch = self._output_repo.active_branch.name
        self._output_repo.git.checkout("master")

    def reload_recent_results(self):
        self._output_repo.git.checkout(self._most_recent_branch)

    def update_output_master_logs(self):
        output_branch_name = str(self._output_repo.active_branch)

        output_repo_hash = str(self._output_repo.head.commit)

        self._output_repo.git.checkout("master")

        json_filepath = os.path.join(self.working_dir, self._output_folder, f"{output_branch_name}.json")
        # note: if filename of "log.csv" is changed,
        #  this also has to be changed in the gitattributes of the init repo func
        csv_filepath = os.path.join(self.working_dir, self._output_folder, "log.csv")

        meta_info_dict = {"Output repo branch": output_branch_name,
                          "Output repo commit hash": output_repo_hash,
                          "Project repo commit hash": str(self.head.commit),
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
        self._output_repo.git.commit("-m", output_branch_name)

        self._output_repo.git.checkout(output_branch_name)
        self._most_recent_branch = output_branch_name

    def cache_previous_results(self, branch_name, file_path):
        if self.output_repo.exist_unstaged_changes:
            self.output_repo.stash_all_changes()
            has_stashed_changes = True
        else:
            has_stashed_changes = False

        previous_branch = self.output_repo.active_branch.name
        self.output_repo.git.checkout(branch_name)

        source_filepath = os.path.join(self._output_folder, file_path)

        # target_folder = os.path.join(self._output_folder + "_cached", branch_name)
        target_folder = os.path.join(self._output_folder, "cached", branch_name)
        os.makedirs(target_folder, exist_ok=True)

        target_filepath = os.path.join(target_folder, file_path)

        shutil.copyfile(source_filepath, target_filepath)

        self.output_repo.git.checkout(previous_branch)
        if has_stashed_changes:
            self.output_repo.apply_stashed_changes()

        return target_filepath

    @contextlib.contextmanager
    def load_previous_result_file(self, branch_name, file_path, *args, **kwargs):
        cached_filepath = self.load_previous_result_file(branch_name, file_path)
        file_handle = open(cached_filepath, *args, **kwargs)
        try:
            yield file_handle
        finally:
            file_handle.close()

    def remove_cached_files(self):
        if os.path.exists(self._output_folder + "_cached"):
            shutil.rmtree(self._output_folder + "_cached")

    def enter_context(self, ):
        self.test_for_uncommitted_changes()
        output_repo = self.output_repo

        if output_repo.exist_unstaged_changes:
            proceed = input(f'The output directory contains the following uncommitted changes:\n'
                            f'{output_repo.untracked_files + output_repo.changed_files}\n'
                            f' These will be lost if you continue\n'
                            f'Proceed? Y/n \n')
            if not (proceed.lower() == "y" or proceed == ""):
                raise KeyboardInterrupt
            # reset all tracked files to previous commit, -q silences output
            output_repo.git.reset("-q", "--hard", "HEAD")
            # remove all untracked files and directories, -q silences output
            output_repo.git.clean("-q", "-f", "-d")

        output_repo.delete_active_branch()  # rename to make more transparent why

        new_branch_name = self.get_new_output_branch_name()
        output_repo.prepare_new_branch(new_branch_name)
        return new_branch_name

    def exit_context(self, message):
        self.test_for_uncommitted_changes()

        print("Completed computations, commiting results")
        self.output_repo.git.add(".")
        commit_return = self.output_repo.git.commit("-m", message)

        print("\n" + commit_return + "\n")

        self.update_output_master_logs()
        self.remove_cached_files()

    @contextlib.contextmanager
    def track_results(self, results_commit_message: str):
        new_branch_name = self.enter_context()
        try:
            yield new_branch_name
        except Exception as e:
            raise e
        else:
            self.exit_context(message=results_commit_message)


class ResultsRepo(BaseRepo):
    pass


class TrackResults:
    def __init__(self, results_commit_message: str, repo_path: str = None):
        if repo_path is None:
            print("DataContext started without explicit repo_path. Trying current working directory")
            self.repo = ProjectRepo(".")
        else:
            self.repo = ProjectRepo(repo_path)

        self.message = results_commit_message

    def __enter__(self):
        self.repo.test_for_uncommitted_changes()
        output_repo = self.repo.output_repo

        if output_repo.exist_unstaged_changes:
            proceed = input(f'The output directory contains the following uncommitted changes:\n'
                            f'{output_repo.untracked_files + output_repo.changed_files}\n'
                            f' These will be lost if you continue\n'
                            f'Proceed? Y/n \n')
            if not (proceed.lower() == "y" or proceed == ""):
                raise KeyboardInterrupt
            # reset all tracked files to previous commit, -q silences output
            output_repo.git.reset("-q", "--hard", "HEAD")
            # remove all untracked files and directories, -q silences output
            output_repo.git.clean("-q", "-f", "-d")

        output_repo.delete_active_branch()

        new_branch_name = self.repo.get_new_output_branch_name()
        output_repo.prepare_new_branch(new_branch_name)

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.repo.test_for_uncommitted_changes()

        if exc_type is None:
            print("Completed computations, commiting results")
            self.repo.output_repo.git.add(".")
            commit_return = self.repo.output_repo.git.commit("-m", self.message)

            print("\n" + commit_return + "\n")

            self.repo.update_output_master_logs()
            self.repo.remove_cached_files()


def add_linebreaks(input_list):
    return [line + "\n" for line in input_list]


def init_lfs(lfs_filetypes):
    os.system(f"git lfs install")
    lfs_filetypes_string = " ".join(lfs_filetypes)
    os.system(f"git lfs track {lfs_filetypes_string}")


def write_lines_to_file(path, lines):
    with open(path, "a") as f:
        f.writelines(add_linebreaks(lines))


def is_tool(name):
    """Check whether `name` is on PATH and marked as executable."""

    from shutil import which

    return which(name) is not None


def initialize_git_repo(path_to_repo, output_repo_name: str = "output", gitignore: list = None,
                        gitattributes: list = None, lfs_filetypes: list = None,
                        output_repo_kwargs: dict = None):
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
        lfs_filetypes = ["*.jpg", "*.png", "*.xlsx", "*.m5", "*.ipynb", "*.pfd"]

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

    if output_repo_name:
        # This means we are in the project repo and should now initialize the output_repo
        initialize_git_repo(output_repo_name, output_repo_name=False, **output_repo_kwargs)
        # This instance of ProjectRepo is therefore the project repo
        repo = ProjectRepo(".", output_folder=output_repo_name)
    else:
        # If output_repo_name is False we are in the output_repo and should finish by committing the changes
        repo = ResultsRepo(".")

    repo.git.add(".")
    repo.git.commit("-m", "initial commit")

    os.chdir(starting_directory)
    return


def example_generate_results_array(seed=None):
    import numpy as np

    if seed is not None:
        np.random.seed(seed)

    results_array = np.random.random((500, 3))
    np.savetxt(os.path.join("output", "result.csv"), results_array, delimiter=",")
    return results_array


def example_generate_results_figures(input_array):
    import matplotlib.pyplot as plt
    import numpy as np

    plt.figure()
    plt.scatter(np.arange(0, 500), input_array[:, 0], alpha=0.5)
    plt.scatter(np.arange(0, 500), input_array[:, 1], alpha=0.5)
    plt.scatter(np.arange(0, 500), input_array[:, 2], alpha=0.5)
    plt.savefig(os.path.join("output", "fig.png"))
    plt.savefig(os.path.join("output", "fig.jpg"), dpi=5000)
    plt.savefig(os.path.join("output", f"fig_{np.random.randint(265)}_{random.randint(0, 1000)}.png"))


def alter_code():
    # Add changes to the project code
    random_number = random.randint(0, 265)
    # random_number = 42
    with open("random_number.txt", "a") as file:
        file.write(str(random_number))
    return random_number


def example_usage():
    """ Pretend this is a python file """

    home_dir = os.path.expanduser("~")
    os.chdir(os.path.join(home_dir, 'ModSimData'))

    random_number = alter_code()

    project_repo = ProjectRepo(".")
    project_repo.full_commit(message="fixed super important bug", update_packages=False)

    with project_repo.track_results(results_commit_message="Add figures and array"):
        # Generate data
        print("Generating results output")
        results_array = example_generate_results_array(seed=random_number)
        example_generate_results_figures(results_array)


def example_write_array():
    """ Pretend this is a python file """

    home_dir = os.path.expanduser("~")
    os.chdir(os.path.join(home_dir, 'ModSimData'))

    # Add changes to the project code
    random_number = random.randint(0, 265)
    # random_number = 42
    with open(f"random_number_{random_number}.txt", "a") as file:
        file.write(str(random_number))

    project_repo = ProjectRepo(".")
    project_repo.full_commit("add code that writes an array to file", update_packages=False)

    with project_repo.track_results(results_commit_message="Add array"):
        example_generate_results_array()

    branch_name = str(project_repo.output_repo.active_branch)
    return branch_name


def example_load(branch_name):
    """ Pretend this is a python file """
    import numpy as np
    """ move into home directory """

    home_dir = os.path.expanduser("~")
    os.chdir(os.path.join(home_dir, 'ModSimData'))

    # Add changes to the project code
    random_number = random.randint(0, 265)
    # random_number = 42
    with open(f"random_number_{random_number}.txt", "a") as file:
        file.write(str(random_number))

    project_repo = ProjectRepo(".")
    project_repo.full_commit("add code that creates figures based on an array", update_packages=False)

    with project_repo.track_results(results_commit_message="Add figures"):
        cached_array_path = project_repo.cache_previous_results(branch_name=branch_name,
                                                                file_path="result.csv")
        previous_array = np.loadtxt(cached_array_path, delimiter=",")

        # with project_repo.load_previous_result_file(branch_name=branch_name,
        #                                               file_path="result.csv") as file_handle:
        #     pass
        example_generate_results_figures(previous_array)

    branch_name = str(project_repo.output_repo.active_branch)
    return branch_name


def example_load_large(branch_name1, branch_name2):
    """ Pretend this is a python file """
    import numpy as np
    """ move into home directory """

    home_dir = os.path.expanduser("~")
    os.chdir(os.path.join(home_dir, 'ModSimData'))

    # Add changes to the project code
    random_number = random.randint(0, 265)
    # random_number = 42
    with open(f"random_number_{random_number}.txt", "a") as file:
        file.write(str(random_number))

    project_repo = ProjectRepo(".")
    project_repo.full_commit("add code that creates figures based on an array", update_packages=False)

    with project_repo.track_results(results_commit_message="Add figures"):
        # cached_fig_path = project_repo.cache_previous_results(branch_name=branch_name2,
        #                                                       file_path="fig.jpg")
        cached_array_path = project_repo.cache_previous_results(branch_name=branch_name1,
                                                                file_path="result.csv")
        previous_array = np.loadtxt(cached_array_path, delimiter=",")

        example_generate_results_figures(previous_array)

    branch_name = str(project_repo.output_repo.active_branch)
    return branch_name


def example_two_step_process():
    branch_name = example_write_array()
    branch_name2 = example_load(branch_name)
    example_load_large(branch_name, branch_name2)


def create_example_repo():
    os.chdir(os.path.expanduser("~"))

    """ initialize Project directory """
    if not os.path.exists("ModSimData"):
        initialize_git_repo("ModSimData")


if __name__ == '__main__':
    # pass

    # create_example_repo()
    example_usage()
    example_two_step_process()
