import os
import json
import sys
import traceback
from datetime import datetime
import shutil
import contextlib
import glob
from stat import S_IREAD, S_IWRITE
from urllib.request import urlretrieve

from tabulate import tabulate
import pandas as pd

try:
    import git
except ImportError:
    # Adding this hint to save users the confusion of trying $pip install git
    raise ImportError("No module named git, please install the gitpython package")

from cadetrdm.utils import ssh_url_to_http_url


def recursive_chmod(path, setting):
    for dirpath, dirnames, filenames in os.walk(path):
        os.chmod(dirpath, setting)
        for filename in filenames:
            os.chmod(os.path.join(dirpath, filename), setting)


def delete_path(filename):
    def remove_readonly(func, path, exc_info):
        # Clear the readonly bit and reattempt the removal
        # ERROR_ACCESS_DENIED = 5
        if func not in (os.unlink, os.rmdir) or exc_info[1].winerror != 5:
            raise exc_info[1]
        os.chmod(path, S_IWRITE)
        func(path)

    absolute_path = os.path.abspath(filename)
    if os.path.isdir(absolute_path):
        shutil.rmtree(absolute_path, onerror=remove_readonly)
    else:
        os.remove(absolute_path)


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

        self.add = self._git.add

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

    @property
    def tags(self):
        return None

    def add_remote(self, remote_url, remote_name="origin"):
        """
        ToDO add documentation
        :param remote_url:
        :param remote_name:
        :return:
        """
        self._git_repo.create_remote(remote_name, url=remote_url)

    def checkout(self, *args, **kwargs):
        self._most_recent_branch = self.active_branch
        self._git.checkout(*args, **kwargs)

    def push(self, remote=None, local_branch=None, remote_branch=None, push_all=True):
        """
        Push local branch to remote.

        :param remote:
            Name of the remote to push to.
        :param local_branch:
            Name of the local branch to push.
        :param remote_branch:
            Name of the remote branch to push to.
        :return:
        """
        if local_branch is None:
            local_branch = self.active_branch
        if remote_branch is None:
            remote_branch = local_branch
        if remote is None:
            if len(self._git_repo.remotes) == 0:
                raise RuntimeError("No remote has been set for this repository yet.")
            remote = [str(remote.name) for remote in self._git_repo.remotes][0]

        remote_interface = self._git_repo.remotes[remote]

        if push_all:
            push_results = remote_interface.push(all=True)
        else:
            push_results = remote_interface.push(refspec=f'{local_branch}:{remote_branch}')

        for push_res in push_results:
            print(push_res.summary)

        if hasattr(self, "output_repo") and push_all:
            self.output_repo.push()

    def delete_active_branch_if_branch_is_empty(self):
        """
        Delete the currently active branch and checkout the master branch
        :return:
        """
        previous_branch = self.active_branch.name
        if previous_branch == "master":
            return

        commit_of_current_master = str(self._git.rev_parse("master"))
        commit_of_current_branch = str(self.head.commit)
        if commit_of_current_branch == commit_of_current_master:
            print("Removing empty branch", previous_branch)
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
        self.add(".")

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
        try:
            self._git.clean("-q", "-f", "-d")
        except git.exc.GitCommandError:
            recursive_chmod(self.working_dir, S_IWRITE)
            self._git.clean("-q", "-f", "-d")

    @property
    def changed_files(self):
        changed_files = self._git.diff(None, name_only=True).split('\n')
        if "" in changed_files:
            changed_files.remove("")
        return changed_files

    @property
    def exist_uncomitted_changes(self):
        return len(self._git.status("--porcelain")) > 0

    def dump_package_list(self, target_folder):
        """
        Use "conda env export" and "pip freeze" to create environment.yml and pip_requirements.txt files.
        """
        if target_folder is not None:
            dump_path = target_folder
        else:
            dump_path = self.working_dir
        print("Dumping conda environment.yml, this might take a moment.")
        os.system(f"conda env export > {dump_path}/conda_environment.yml")
        print("Dumping conda independent environment.yml, this might take a moment.")
        os.system(f"conda env export --from-history > {dump_path}/conda_independent_environment.yml")
        print("Dumping pip requirements.txt.")
        os.system(f"pip freeze > {dump_path}/pip_requirements.txt")
        print("Dumping pip independent requirements.txt.")
        os.system(f"pip list --not-required --format freeze > {dump_path}/pip_independent_requirements.txt")

    def commit(self, message: str, add_all=True):
        """
        Commit current state of the repository.

        :param message:
            Commit message
        :param add_all:
            Option to add all changed and new files to git automatically.
        """
        if not self.exist_uncomitted_changes:
            print(f"No changes to commit in repo {self.working_dir}")
            return

        print(f"Commiting changes to repo {self.working_dir}")
        if add_all:
            self.add(".")
        try:
            commit_return = self._git.commit("-m", message)
            print("\n" + commit_return + "\n")
        except:
            pass

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
        if not self.exist_uncomitted_changes:
            raise RuntimeError("No changes in repo to stash.")
        self.add(".")
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
        try:
            # Remove previous code backup
            code_backup_path = os.path.join(self.working_dir, "logs", "code_backup")
            shutil.rmtree(code_backup_path, ignore_errors=True)
        except Exception as e:
            print(e)
        try:
            # Remove previous logs
            logs_path = os.path.join(self.working_dir, "logs")
            shutil.rmtree(logs_path, ignore_errors=True)
        except Exception as e:
            print(e)

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
        if self.exist_uncomitted_changes:
            raise RuntimeError(f"Found uncommitted changes in the repository {self.working_dir}.")

    def add_list_of_remotes_in_readme_file(self, repo_identifier: str, remotes_url_list: list):
        if len(remotes_url_list) > 0:
            remotes_url_list_http = [ssh_url_to_http_url(remote)
                                     for remote in remotes_url_list]
            output_link_line = " and ".join(f"[{repo_identifier}]({output_repo_remote})"
                                            for output_repo_remote in remotes_url_list_http) + "\n"

            readme_filepath = os.path.join(self.working_dir, "README.md")
            with open(readme_filepath, "r") as file_handle:
                filelines = file_handle.readlines()
                filelines_giving_output_repo = [i for i in range(len(filelines))
                                                if filelines[i].startswith(f"[{repo_identifier}](")]
                if len(filelines_giving_output_repo) == 1:
                    line_to_be_modified = filelines_giving_output_repo[0]
                    filelines[line_to_be_modified] = output_link_line
                elif len(filelines_giving_output_repo) == 0:
                    filelines.append("The output repo can be found at:\n")
                    filelines.append(output_link_line)
                else:
                    raise RuntimeError(f"Multiple lines in the README.md at {readme_filepath}"
                                       f" link to the {repo_identifier}. "
                                       "Can't automatically update the link.")

            with open(readme_filepath, "w") as file_handle:
                file_handle.writelines(filelines)


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
            output_folder = os.path.split(output_folder)[-1]
            self.output_folder = output_folder
        else:
            with open(os.path.join(repository_path, "output_remotes.json"), "r") as handle:
                data = json.load(handle)
            self.output_folder = data["output_folder_name"]

        self._output_repo = ResultsRepo(os.path.join(self.working_dir, self.output_folder))
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
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        branch_name = "_".join([timestamp, self.output_folder, "from", str(self.active_branch), project_repo_hash[:7]])
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

    def print_output_log(self):
        def insert_newlines(string, every=30):
            lines = []
            for i in range(0, len(string), every):
                lines.append(string[i:i + every])
            return '\n'.join(lines)

        self.output_repo.checkout("master")

        csv_filepath = os.path.join(self.working_dir, self.output_folder, "logs", "log.csv")

        df = pd.read_csv(csv_filepath, sep=",", header=0)
        # Clean up the headers
        df = df.rename(columns={"Output repo commit message": 'Output commit message',
                                "Output repo branch": "Output branch",
                                "Output repo commit hash": "Output hash", "Project repo commit hash": "Project hash"})
        # Shorten the commit hashes
        df.loc[:, "Output hash"] = df.loc[:, "Output hash"].apply(lambda x: x[:8])
        # Shorten commit messages
        df.loc[:, "Output commit message"] = df.loc[:, "Output commit message"].apply(lambda x: x[:55])
        df.loc[:, "Output commit message"] = df.loc[:, "Output commit message"].apply(insert_newlines)

        # Select only columns of interest
        df = df.loc[:, ["Output commit message", "Output hash", "Output branch"]]

        # Print
        print(tabulate(df, headers=df.columns, showindex=False))

        self.output_repo.checkout(self.output_repo._most_recent_branch)

    def update_output_master_logs(self, ):
        """
        Dumps all the metadata information about the project repositories state and
        the commit hash and branch name of the ouput repository into the master branch of
        the output repository.
        """
        output_branch_name = str(self._output_repo.active_branch)

        output_repo_hash = str(self._output_repo.head.commit)
        output_commit_message = self._output_repo.active_branch.commit.message
        output_commit_message = output_commit_message.replace("\n", "; ")

        self._output_repo._git.checkout("master")

        logs_folderpath = os.path.join(self.working_dir, self.output_folder, "logs")
        if not os.path.exists(logs_folderpath):
            os.makedirs(logs_folderpath)

        json_filepath = os.path.join(logs_folderpath, f"{output_branch_name}.json")
        # note: if filename of "log.csv" is changed,
        #  this also has to be changed in the gitattributes of the init repo func
        csv_filepath = os.path.join(logs_folderpath, "log.csv")

        meta_info_dict = {
            "Output repo commit message": output_commit_message,
            "Output repo branch": output_branch_name,
            "Output repo commit hash": output_repo_hash,
            "Project repo commit hash": str(self.head.commit),
            "Project repo folder name": os.path.split(self.working_dir)[-1],
            "Project repo remotes": [str(remote.url) for remote in self.remotes],
            "Python sys args": str(sys.argv),
            "Tags": self.tags,
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

        self.dump_package_list(logs_folderpath)

        # Copy all code files from the project git repo to the output repo
        code_copy_folderpath = os.path.join(logs_folderpath, "code_backup")
        if not os.path.exists(code_copy_folderpath):
            os.makedirs(code_copy_folderpath)
        self.copy_code(code_copy_folderpath)

        self._output_repo.add(".")
        self._output_repo._git.commit("-m", f"log for '{output_commit_message}' \n"
                                            f"of branch '{output_branch_name}'")

        self._output_repo._git.checkout(output_branch_name)
        self._most_recent_branch = output_branch_name

    def copy_code(self, target_path):
        for file in self._git.ls_files().split("\n"):
            if "\\" in file:
                file = bytes(file, "utf-8").decode("unicode_escape").encode("cp1252").decode("utf-8")
            if "'" in file or '"' in file:
                file = file.replace("'", "").replace('"', '')
            try:
                target_file_path = os.path.join(self.working_dir, target_path, file)
                target_folder = os.path.split(target_file_path)[0]
                if not os.path.exists(target_folder):
                    os.makedirs(target_folder)
                shutil.copyfile(
                    os.path.join(self.working_dir, file),
                    target_file_path
                )
            except:
                traceback.print_exc()

    def commit(self, message: str, add_all=True):
        """
        Commit current state of the repository.

        :param message:
            Commit message
        :param add_all:
            Option to add all changed and new files to git automatically.
        """

        output_repo_remotes = [str(remote.url) for remote in self.output_repo.remotes]
        self.add_list_of_remotes_in_readme_file("output_repo", output_repo_remotes)

        output_json_filepath = os.path.join(self.working_dir, "output_remotes.json")
        with open(output_json_filepath, "w") as file_handle:
            remotes_dict = {remote.name: str(remote.url) for remote in self.output_repo.remotes}
            json_dict = {"output_folder_name": self.output_folder, "output_remotes": remotes_dict}
            json.dump(json_dict, file_handle, indent=2)

        super().commit(message=message, add_all=add_all)

    def load_external_repository(self, url, branch=None, commit=None, name=None, path=None, ):
        """
        Load an external git repository as a git submodule into this repository.

        :param url:
            URL of the git repository.
        :param branch:
            Branch of the external repository to check out.
        :param commit:
            Commit of the external repository to check out.
        :param name:
            Optional custom name for the repository.
        :param path:
            Optional custom relative path where the repository should be placed.
        :return:
        """
        if path is None or name is None:
            if "/" in url:
                sep = "/"
            elif "\\" in url:
                sep = "\\"
            else:
                raise RuntimeError("Could not automatically extract name from URL"
                                   " because the URL is not of a known format")

            if path is None:
                repo_name = url.split(sep)[-1]
                path = os.path.join("external_repos", repo_name)
            if name is None:
                name = url.split(sep)[-1]

        self._git_repo.create_submodule(name=name, url=url, branch=branch, path=path)
        if commit is not None:
            submodule = BaseRepo(path)
            submodule._git.checkout(commit)
        full_path = os.path.join(self.working_dir, path)
        return full_path

    def download_file(self, url, file_path):
        """
        Download the file from the url and put it in the output+file_path location.

        :param file_path:
        :param url:
        :return:
            Returns a tuple containing the path to the newly created
            data file as well as the resulting HTTPMessage object.
        """
        absolute_file_path = self.output_data(file_path)
        return urlretrieve(url, absolute_file_path)

    def input_data(self, file_path, branch_name=None):
        """
        # ToDo: needs testing!
        Load previously generated results to iterate upon.
        :param file_path:
            Can be relative path within the cached output repository to the file you wish to load.
            OR relative path within the actual output repository, if branch_name is given.
        :param branch_name:
            Name of the branch of the output repository in which the results are stored. If none,
            the cached_output is used.
        :return:
            Absolute path to the newly copied file.
        """
        if branch_name is None and os.path.exists(file_path):
            return file_path

        if branch_name is None and not os.path.exists(file_path):
            branch_name_and_path = file_path.split("_cached")[-1]
            if os.sep not in branch_name_and_path:
                sep = "/"
            else:
                sep = os.sep
            branch_name, file_path = file_path.split(sep, maxsplit=1)

        if self.output_repo.exist_uncomitted_changes:
            self.output_repo.stash_all_changes()
            has_stashed_changes = True
        else:
            has_stashed_changes = False

        previous_branch = self.output_repo.active_branch.name
        self.output_repo._git.checkout(branch_name)

        source_filepath = os.path.join(self.output_repo.working_dir, file_path)

        target_folder = os.path.join(self.output_repo.working_dir + "_cached", branch_name)
        os.makedirs(target_folder, exist_ok=True)

        target_filepath = os.path.join(target_folder, file_path)
        if os.path.exists(target_filepath):
            os.chmod(target_filepath, S_IWRITE)
            os.remove(target_filepath)
        shutil.copyfile(source_filepath, target_filepath)
        os.chmod(target_filepath, S_IREAD)

        self.output_repo._git.checkout(previous_branch)
        if has_stashed_changes:
            self.output_repo.apply_stashed_changes()

        return target_filepath

    def output_data(self, sub_path):
        """
        Return an absolute path with the repo_dir/output_dir/sub_path

        :param sub_path:
        :return:
        """
        return os.path.join(self.working_dir, self.output_repo.working_dir, sub_path)

    def remove_cached_files(self):
        """
        Delete all previously cached results.
        """
        if os.path.exists(self.output_repo.working_dir + "_cached"):
            shutil.rmtree(self.output_repo.working_dir + "_cached")

    def test_for_correct_repo_setup(self):
        """
        ToDo: implement
        :return:
        """

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
        self.test_for_correct_repo_setup()
        self.test_for_uncommitted_changes()
        self._on_context_enter_commit_hash = self.current_commit_hash
        self._is_in_context_manager = True
        output_repo = self.output_repo

        if output_repo.exist_uncomitted_changes:
            output_repo.reset_hard_to_head()

        output_repo.delete_active_branch_if_branch_is_empty()

        new_branch_name = self.get_new_output_branch_name()

        # update urls in master branch of output_repo
        output_repo._git.checkout("master")
        project_repo_remotes = [str(remote.url) for remote in self.remotes]
        output_repo.add_list_of_remotes_in_readme_file("project_repo", project_repo_remotes)
        output_repo.commit("Update urls")

        output_repo.prepare_new_branch(new_branch_name)
        return new_branch_name

    def copy_data_to_cache(self):
        """
        Copy all existing output results into a cached folder and make it read-only.

        :return:
        """
        try:
            source_filepath = self.output_repo.working_dir

            branch_name = self.output_repo.active_branch.name

            target_folder = os.path.join(self.output_repo.working_dir + "_cached", branch_name)

            shutil.copytree(source_filepath, target_folder)

            # delete all .git files from the cache
            for filename in glob.iglob(f"{target_folder}/**/.git*", recursive=True):
                delete_path(filename)

            # Set all files to read only
            for filename in glob.iglob(f"{target_folder}/**/*", recursive=True):
                absolute_path = os.path.abspath(filename)
                if os.path.isdir(absolute_path):
                    continue
                os.chmod(os.path.abspath(filename), S_IREAD)
        except:
            traceback.print_exc()

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
        self.output_repo.add(".")
        try:
            # This has to be using ._git.commit to raise an error if no results have been written.
            commit_return = self.output_repo._git.commit("-m", message)
            self.copy_data_to_cache()
            self.update_output_master_logs()
            print("\n" + commit_return + "\n")
        except git.exc.GitCommandError as e:
            self.output_repo.delete_active_branch_if_branch_is_empty()
            raise e
        finally:
            # self.remove_cached_files()
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
            self.output_repo.delete_active_branch_if_branch_is_empty()
            raise e
        else:
            self.exit_context(message=results_commit_message)


class ResultsRepo(BaseRepo):
    pass
