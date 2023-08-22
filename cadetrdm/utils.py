import os
import json
from datetime import datetime
import shutil
import contextlib
import click

try:
    import git
except ImportError:
    # Adding this hint to save users the confusion of trying $pip install git
    raise ImportError("No module named git, please install the gitpython package")


class BaseRepo:
    def __init__(self, repository_path=None, search_parent_directories=False, *args, **kwargs):
        """
        Base class handling most git workflows.

        :param repository_path:
            Path to the root directory of the repository.
        :param search_parent_directories:
            if True, all parent directories will be searched for a valid repo as well.

            Please note that this was the default behaviour in older versions of GitPython,
            which is considered a bug though.
        :param args:
            Args handed to git.Repo()
        :param kwargs:
            Kwargs handed to git.Repo()
        """
        if repository_path is None or repository_path == ".":
            repository_path = os.getcwd()
        self._git_repo = git.Repo(repository_path, search_parent_directories=search_parent_directories, *args, **kwargs)
        self._git = self._git_repo.git

        self._most_recent_branch = self.active_branch.name
        self._earliest_commit = None

    @property
    def active_branch(self):
        return self._git_repo.active_branch

    @property
    def untracked_files(self):
        return self._git_repo.untracked_files

    @property
    def current_commit_hash(self):
        return str(self.head.commit)

    @property
    def working_dir(self):
        return self._git_repo.working_dir

    @property
    def head(self):
        return self._git_repo.head

    @property
    def remotes(self):
        return self._git_repo.remotes

    @property
    def earliest_commit(self):
        if self._earliest_commit is None:
            *_, earliest_commit = self._git_repo.iter_commits()
            self._earliest_commit = earliest_commit
        return self._earliest_commit

    # ToDo: test if functools.wraps can keep docstrings
    def add(self, *args, **kwargs):
        self._git.add(*args, **kwargs)

    def add_remote(self, remote_url, remote_name="origin"):
        """
        ToDO add documentation
        :param remote_url:
        :param remote_name:
        :return:
        """
        self._git_repo.create_remote(remote_name, url=remote_url)

    def push(self, remote=None, local_branch=None, remote_branch=None):
        """
        # ToDo extend documentation
        :param remote:
        :param local_branch:
        :param remote_branch:
        :return:
        """
        if local_branch is None:
            local_branch = self.active_branch
        if remote_branch is None:
            remote_branch = local_branch
        if remote is None:
            remote = list(sorted(self._git_repo.remotes.keys()))[0]

        remote_interface = self._git_repo.remotes[remote]
        remote_interface.push(refspec=f'{local_branch}:{remote_branch}')

    def delete_active_branch_if_branch_is_empty(self):
        """
        Delete the currently active branch and checkout the master branch
        :return:
        """
        previous_branch = self.active_branch.name
        if str(self.head.commit) == self.earliest_commit:
            self._git.checkout("master")
            self._git.branch("-d", previous_branch)

    def add_all_files(self, automatically_add_new_files=True):
        """
        Stage all changes to git. This includes new, untracked files as well as modified files.
        :param automatically_add_new_files:
            If this is set to false a user input will be prompted if untracked files are about to be added.
        :return:
            List of all staged changes.
        """
        untracked_files = ""
        if len(self.untracked_files) > 0:
            untracked_files = "\n".join(["- " + file for file in self.untracked_files])

        if automatically_add_new_files:
            for f in self.untracked_files:
                self._git.add(f)
        else:
            proceed = input(
                f'Found untracked files. Adding the following untracked files to git: \n{untracked_files}\n'
                f'Proceed? Y/n \n'
            )
            if proceed.lower() == "y" or proceed == "":
                for f in self.untracked_files:
                    self._git.add(f)
            else:
                raise KeyboardInterrupt

        changed_files = self.changed_files
        for f in changed_files:
            self._git.add(f)
        return self.untracked_files + changed_files

    def reset_hard_to_head(self):
        proceed = input(f'The output directory contains the following uncommitted changes:\n'
                        f'{self.untracked_files + self.changed_files}\n'
                        f' These will be lost if you continue\n'
                        f'Proceed? Y/n \n')
        if not (proceed.lower() == "y" or proceed == ""):
            raise KeyboardInterrupt
        # reset all tracked files to previous commit, -q silences output
        self._git.reset("-q", "--hard", "HEAD")
        # remove all untracked files and directories, -q silences output
        self._git.clean("-q", "-f", "-d")

    @property
    def changed_files(self):
        changed_files = self._git.diff(None, name_only=True).split('\n')
        if "" in changed_files:
            changed_files.remove("")
        return changed_files

    @property
    def exist_unstaged_changes(self):
        return len(self.untracked_files) > 0 or len(self.changed_files) > 0

    def update_package_list(self):
        """
        Use "conda env export" and "pip freeze" to create environment.yml and pip_requirements.txt files.
        """
        repo_path = self.working_dir
        print("Dumping conda environment.yml, this might take a moment.")
        os.system(f"conda env export > {repo_path}/conda_environment.yml")
        print("Dumping conda independent environment.yml, this might take a moment.")
        os.system(f"conda env export --from-history > {repo_path}/conda_independent_environment.yml")
        print("Dumping pip requirements.txt.")
        os.system(f"pip freeze > {repo_path}/pip_requirements.txt")
        print("Dumping pip independent requirements.txt.")
        os.system(f"pip list --not-required --format freeze > {repo_path}/pip_independent_requirements.txt")

    def commit(self, message: str, add_all=True, update_packages=True):
        """
        Commit current state of the repository.

        :param message:
            Commit message
        :param add_all:
            Option to add all changed and new files to git automatically.
        :param update_packages:
            Option to automatically dump the python environment information into environment.yml files.
        """
        if not self.exist_unstaged_changes:
            print(f"No changes to commit in repo {self.working_dir}")
            return

        print(f"Commiting changes to repo {self.working_dir}")
        if update_packages:
            self.update_package_list()
        if add_all:
            self.add_all_files()
        commit_return = self._git.commit("-m", message)
        print("\n" + commit_return + "\n")

    def git_ammend(self, ):
        """
        Call git commit with options --amend --no-edit
        """
        self._git.commit("--amend", "--no-edit")

    @property
    def status(self):
        return self._git.status()

    @property
    def log(self):
        return self._git.log()

    def log_oneline(self):
        return self._git.log("--oneline")

    def print_status(self):
        """
        prints git status
        """
        print(self._git.status())

    def print_log(self):
        """
        Prints the git log
        """
        print(self._git.log())

    def stash_all_changes(self):
        """
        Adds all untracked files to git and then stashes all changes.
        Will raise a RuntimeError if no changes are found.
        """
        if not self.exist_unstaged_changes:
            raise RuntimeError("No changes in repo to stash.")
        self._git.add(".")
        self._git.stash()

    def prepare_new_branch(self, branch_name):
        """
        Prepares a new branch to recieve data. This includes:
         - checking out the master branch,
         - creating a new branch from there
        This thereby produces a clear, empty directory for data, while still maintaining
        .gitignore and .gitatributes
        :param branch_name:
            Name of the new branch.
        """
        self._git.checkout("master")
        self._git.checkout('-b', branch_name)  # equivalent to $ git checkout -b %branch_name

    def apply_stashed_changes(self):
        """
        Apply the last stashed changes.
        If a "CONFLICT (modify/delete)" error is encountered, this is ignored.
        All other errors are raised.
        """
        try:
            self._git.stash('pop')  # equivalent to $ git stash pop
        except git.exc.GitCommandError as e:
            # Will raise error because the stash cannot be applied without conflicts. This is expected
            if 'CONFLICT (modify/delete)' in e.stdout:
                pass
            else:
                raise e

    def test_for_uncommitted_changes(self):
        """
        Raise a RuntimeError if uncommitted changes are in the repository.
        :return:
        """
        if self.exist_unstaged_changes:
            raise RuntimeError(f"Found uncommitted changes in the repository {self.working_dir}.")


class ProjectRepo(BaseRepo):
    def __init__(self, repository_path=None, output_folder=None,
                 search_parent_directories=True, *args, **kwargs):
        """
        Class for Project-Repositories. Handles interaction between the project repo and
        the output (i.e. results) repo.

        :param repository_path:
            Path to the root of the git repository.
        :param output_folder:
            Path to the root of the output repository.
        :param search_parent_directories:
            if True, all parent directories will be searched for a valid repo as well.

            Please note that this was the default behaviour in older versions of GitPython,
            which is considered a bug though.
        :param args:
            Additional args to be handed to BaseRepo.
        :param kwargs:
            Additional kwargs to be handed to BaseRepo.
        """

        super().__init__(repository_path, search_parent_directories=search_parent_directories, *args, **kwargs)

        if output_folder is not None:
            self._output_folder = output_folder
        elif output_folder is None:
            self._output_folder = "output"

        self._output_repo = ResultsRepo(os.path.join(self.working_dir, self._output_folder))
        self._on_context_enter_commit_hash = None
        self._is_in_context_manager = False

    @property
    def output_repo(self):
        if self._output_repo is None:
            raise ValueError("The output repo has not been set yet.")
        return self._output_repo

    def get_new_output_branch_name(self):
        """
        Construct a name for the new branch in the output repository.
        :return: the new branch name
        """
        project_repo_hash = str(self.head.commit)
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")[:-4]
        branch_name = "_".join([str(self.active_branch), project_repo_hash[:7], self._output_folder, timestamp])
        return branch_name

    def check_results_master(self):
        """
        Checkout the master branch, which contains all the log files.
        """
        self._most_recent_branch = self._output_repo.active_branch.name
        self._output_repo._git.checkout("master")

    def reload_recent_results(self):
        """
        Checkout the most recent previous branch.
        """
        self._output_repo._git.checkout(self._most_recent_branch)

    def update_output_master_logs(self):
        """
        Dumps all the metadata information about the project repositories state and
        the commit hash and branch name of the ouput repository into the master branch of
        the output repository.
        """
        output_branch_name = str(self._output_repo.active_branch)

        output_repo_hash = str(self._output_repo.head.commit)

        self._output_repo._git.checkout("master")

        json_filepath = os.path.join(self.working_dir, self._output_folder, f"{output_branch_name}.json")
        # note: if filename of "log.csv" is changed,
        #  this also has to be changed in the gitattributes of the init repo func
        csv_filepath = os.path.join(self.working_dir, self._output_folder, "log.csv")

        meta_info_dict = {"Output repo branch": output_branch_name,
                          "Output repo commit hash": output_repo_hash,
                          "Project repo commit hash": str(self.head.commit),
                          "Project repo folder name": os.path.split(self.working_dir)[-1],
                          "Project repo remotes": [str(remote.url) for remote in self.remotes],
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

        self._output_repo._git.add(".")
        self._output_repo._git.commit("-m", output_branch_name)

        self._output_repo._git.checkout(output_branch_name)
        self._most_recent_branch = output_branch_name

    def load_external_data(self, url, name=None, path=None, branch=None, commit=None):
        """
        name: str,
        path: PathLike,
        url: Union[str, None] = None,
        branch: Union[str, None] = None,"""
        if path is None:
            repo_name = url.split("/")[-1]
            path = os.path.join("external_repos", repo_name)
        if name is None:
            name = url.split("/")[-1]

        self._git_repo.create_submodule(name=name, url=url, branch=branch, path=path)
        if commit is not None:
            submodule = BaseRepo(path)
            submodule._git.checkout(commit)

    def load_previous_results(self, branch_name, file_path):
        """
        Load previously generated results to iterate upon.
        :param branch_name:
            Name of the branch of the output repository in which the results are stored
        :param file_path:
            Relative path within the output repository to the file you wish to load.
        :return:
            Absolute path to the newly copied file.
        """
        if self.output_repo.exist_unstaged_changes:
            self.output_repo.stash_all_changes()
            has_stashed_changes = True
        else:
            has_stashed_changes = False

        previous_branch = self.output_repo.active_branch.name
        self.output_repo._git.checkout(branch_name)

        source_filepath = os.path.join(self.output_repo.working_dir, file_path)

        # target_folder = os.path.join(self._output_folder + "_cached", branch_name)
        target_folder = os.path.join(self.output_repo.working_dir, "cached", branch_name)
        os.makedirs(target_folder, exist_ok=True)

        target_filepath = os.path.join(target_folder, file_path)

        shutil.copyfile(source_filepath, target_filepath)

        self.output_repo._git.checkout(previous_branch)
        if has_stashed_changes:
            self.output_repo.apply_stashed_changes()

        return target_filepath

    @contextlib.contextmanager
    def load_previous_result_file(self, branch_name, file_path, *args, **kwargs):
        """
        Context manager around load_previous_result_file that directly opens a handle to the loaded file.
        :param branch_name:
            Name of the branch of the output repository in which the results are stored
        :param file_path:
            Relative path within the output repository to the file you wish to load.
        :param args:
            Args to be handed to the open() function
        :param kwargs:
            kwargs to be handed to the open() function
        :return:
            Handle to the copied file.
        """
        cached_filepath = self.load_previous_result_file(branch_name, file_path)
        file_handle = open(cached_filepath, *args, **kwargs)
        try:
            yield file_handle
        finally:
            file_handle.close()

    def remove_cached_files(self):
        """
        Delete all previously cached results.
        """
        if os.path.exists(self._output_folder + "_cached"):
            shutil.rmtree(self._output_folder + "_cached")

    def enter_context(self, ):
        """
        Enter the tracking context. This includes:
         - Ensure no uncommitted changes in the project repository
         - Remove all uncommitted changes in the output repository
         - Clean up empty branches in the output repository
         - Create a new empty output branch in the output repository

        :return:
            The name of the newly created output branch.
        """
        self.test_for_uncommitted_changes()
        self._on_context_enter_commit_hash = self.current_commit_hash
        self._is_in_context_manager = True
        output_repo = self.output_repo

        if output_repo.exist_unstaged_changes:
            output_repo.reset_hard_to_head()

        output_repo.delete_active_branch_if_branch_is_empty()

        new_branch_name = self.get_new_output_branch_name()
        output_repo.prepare_new_branch(new_branch_name)
        return new_branch_name

    def exit_context(self, message):
        """
        After running all project code, this prepares the commit of the results to the output repository. This includes
         - Ensure no uncommitted changes in the project repository
         - Stage all changes in the output repository
         - Commit all changes in the output repository with the given commit message.
         - Update the log files in the master branch of the output repository.
        :param message:
            Commit message for the output repository commit.
        """
        self.test_for_uncommitted_changes()
        if self._on_context_enter_commit_hash != self.current_commit_hash:
            raise RuntimeError("Code has changed since starting the context. Don't do that.")

        print("Completed computations, commiting results")
        self.output_repo._git.add(".")
        commit_return = self.output_repo._git.commit("-m", message)

        print("\n" + commit_return + "\n")

        self.update_output_master_logs()
        self.remove_cached_files()
        self._is_in_context_manager = False
        self._on_context_enter_commit_hash = None

    @contextlib.contextmanager
    def track_results(self, results_commit_message: str, debug=False):
        """
        Context manager to be used when running project code that produces output that should
        be tracked in the output repository.
        :param results_commit_message:
            Commit message for the commit of the output repository.
        """
        if debug:
            yield "debug"
            return

        new_branch_name = self.enter_context()
        try:
            yield new_branch_name
        except Exception as e:
            raise e
        else:
            self.exit_context(message=results_commit_message)


class ResultsRepo(BaseRepo):
    pass
