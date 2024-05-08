import contextlib
import glob
import json
import os
import shutil
import sys
import traceback
import warnings
from datetime import datetime
from pathlib import Path
from stat import S_IREAD, S_IWRITE
from urllib.request import urlretrieve

import cadetrdm
from cadetrdm.io_utils import delete_path, test_for_lfs
from cadetrdm.io_utils import recursive_chmod, write_lines_to_file, wait_for_user, init_lfs
from cadetrdm.jupyter_functionality import Notebook
from cadetrdm.logging import OutputLog
from cadetrdm.remote_integration import GitHubRemote, GitLabRemote
from cadetrdm.web_utils import ssh_url_to_http_url

try:
    import git
except ImportError:
    # Adding this hint to save users the confusion of trying $pip install git
    raise ImportError("No module named git, please install the gitpython package")


def validate_is_output_repo(path_to_repo):
    with open(os.path.join(path_to_repo, ".cadet-rdm-data.json"), "r") as file_handle:
        rdm_data = json.load(file_handle)
        if rdm_data["is_project_repo"]:
            raise ValueError("Please use the URL to the output repository.")


class BaseRepo:
    def __init__(self, repository_path=None, search_parent_directories=True, *args, **kwargs):
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

        if type(repository_path) is str:
            repository_path = Path(repository_path)

        self._git_repo = git.Repo(repository_path, search_parent_directories=search_parent_directories, *args, **kwargs)
        self._git = self._git_repo.git

        self._most_recent_branch = self.active_branch.name
        self._earliest_commit = None

        self.add = self._git.add

    @property
    def active_branch(self):
        try:
            active_branch = self._git_repo.active_branch
            return active_branch
        except TypeError as e:
            if "HEAD is a detached" in str(e):
                class DetachedHeadBranch:
                    name = "detached_head"

                    def __repr__(self):
                        return "detached_head"

                    def __str__(self):
                        return "detached_head"

                return DetachedHeadBranch()
            else:
                raise e

    @property
    def untracked_files(self):
        return self._git_repo.untracked_files

    @property
    def current_commit_hash(self):
        return str(self.head.commit)

    @property
    def path(self):
        return Path(self._git_repo.working_dir)

    @property
    def bare(self):
        return self._git_repo.bare

    @property
    def working_dir(self):
        print("Deprecation Warning. .working_dir is getting replaced with .path")
        return Path(self._git_repo.working_dir)

    @property
    def head(self):
        return self._git_repo.head

    @property
    def remotes(self):
        return self._git_repo.remotes

    @property
    def remote_urls(self):
        if len(self.remotes) == 0:
            print(RuntimeWarning(f"No remote for repo at {self.path} set yet. Please add remote ASAP."))
        return [str(remote.url) for remote in self.remotes]

    @property
    def earliest_commit(self):
        if self._earliest_commit is None:
            *_, earliest_commit = self._git_repo.iter_commits()
            self._earliest_commit = earliest_commit
        return self._earliest_commit

    @property
    def tags(self):
        return list()

    @property
    def data_json_path(self):
        return self.path / ".cadet-rdm-data.json"

    @property
    def cache_json_path(self):
        return self.path / ".cadet-rdm-cache.json"

    @property
    def has_changes_upstream(self):
        try:
            remote_branches = self.remotes[0].fetch()
            correct_remote_branches = [fetch_info for fetch_info in remote_branches
                                       if self.active_branch.name in fetch_info.name]
            if len(correct_remote_branches) > 1:
                raise RuntimeError(f"Remote has multiple branches matching local branch {self.active_branch.name}: "
                                   f"{[branch.name for branch in correct_remote_branches]}")
            remote_hash = str(correct_remote_branches[0].commit)

            if self.current_commit_hash != remote_hash and remote_hash not in self.log:
                return True
            elif self.current_commit_hash != remote_hash and remote_hash in self.log:
                print("Local repository is ahead of remote. This could be due to CADET-RDM version updates.")
                return False
            else:
                return False

        except git.GitCommandError as e:
            traceback.print_exc()
            print(f"Git command error in {self.path}: {e}")

    def fetch(self):
        self._git.fetch()

    def update(self):
        try:
            self.fetch()

            if self.has_changes_upstream:
                print(f"New changes detected in {self.remotes[0]}, pulling updates...")
                self.remotes[0].pull()
                self._git.reset(["--hard", f"{self.remotes[0]}/{self.active_branch}"])

        except git.GitCommandError as e:
            traceback.print_exc()
            print(f"Git command error in {self.path}: {e}")

    def add_remote(self, remote_url, remote_name=None):
        """
        Add a remote to the repository.

        :param remote_url:
        :param remote_name:
        :return:
        """
        if remote_name is None:
            remote_name = "origin"
        self._git_repo.create_remote(remote_name, url=remote_url)
        with open(self.data_json_path, "r") as handle:
            rdm_data = json.load(handle)
        if rdm_data["is_project_repo"]:
            # This folder is a project repo. Use a project repo class to easily access the output repo.
            output_repo = ProjectRepo(self.path).output_repo

            if output_repo.active_branch != "main":
                if output_repo.exist_uncomitted_changes:
                    output_repo.stash_all_changes()
                output_repo.checkout("main")

            output_repo.add_list_of_remotes_in_readme_file("project_repo", self.remote_urls)
            output_repo.commit("Add remote for project repo", verbosity=0)
        if rdm_data["is_output_repo"]:
            # This folder is an output repo
            project_repo = ProjectRepo(self.path.parent)
            project_repo.update_output_remotes_json()
            project_repo.add_list_of_remotes_in_readme_file("output_repo", self.remote_urls)
            project_repo.commit("Add remote for output repo", verbosity=0)

    def add_filetype_to_lfs(self, file_type):
        """
        Add the filetype given in file_type to the GIT-LFS tracking

        :param file_type:
        Wildcard formatted string. Examples: "*.png" or "*.xlsx"
        :return:
        """
        init_lfs(lfs_filetypes=[file_type], path=self.path)
        self.add_all_files()
        self.commit(f"Add {file_type} to lfs")

    def import_remote_repo(self, source_repo_location, source_repo_branch, target_repo_location=None):
        """
        Import a remote repo and update the cadet-rdm-cache

        :param source_repo_location:
        Path or URL to the source repo.
        Example https://jugit.fz-juelich.de/IBG-1/ModSim/cadet/agile_cadet_rdm_presentation_output.git
        or git@jugit.fz-juelich.de:IBG-1/ModSim/cadet/agile_cadet_rdm_presentation_output.git

        :param source_repo_branch:
        Branch of the source repo to check out.

        :param target_repo_location:
        Place to store the repo. If None, the external_cache folder is used.

        :return:
        Path to the cloned repository
        """
        if "://" in str(source_repo_location):
            source_repo_name = source_repo_location.split("/")[-1]
        else:
            source_repo_name = Path(source_repo_location).name
        if target_repo_location is None:
            target_repo_location = self.path / "external_cache" / source_repo_name
        else:
            target_repo_location = self.path / target_repo_location

        self.add_path_to_gitignore(target_repo_location)

        print(f"Cloning from {source_repo_location} into {target_repo_location}")
        multi_options = ["--filter=blob:none", "--branch", source_repo_branch, "--single-branch"]
        repo = git.Repo.clone_from(source_repo_location, target_repo_location, multi_options=multi_options)
        repo.git.clear_cache()
        repo.close()

        self.update_cadet_rdm_cache_json(source_repo_branch=source_repo_branch,
                                         target_repo_location=target_repo_location,
                                         source_repo_location=source_repo_location)
        return target_repo_location

    def add_path_to_gitignore(self, path_to_be_ignored):
        """
        Add the path to the .gitignore file

        :param path_to_be_ignored:
        :return:
        """
        path_to_be_ignored = self.ensure_relative_path(path_to_be_ignored)
        with open(self.path / ".gitignore", "r") as file_handle:
            gitignore = file_handle.readlines()
            gitignore[-1] += "\n"  # Sometimes there is no trailing newline
        if str(path_to_be_ignored) + "\n" not in gitignore:
            gitignore.append(str(path_to_be_ignored) + "\n")
        with open(self.path / ".gitignore", "w") as file_handle:
            file_handle.writelines(gitignore)

    def update_cadet_rdm_cache_json(self, source_repo_location, source_repo_branch, target_repo_location):
        """
        Update the information in the .cadet_rdm_cache.json file

        :param source_repo_location:
        Path or URL to the source repo.
        :param source_repo_branch:
        Name of the branch to check out.
        :param target_repo_location:
        Path where to put the repo or data
        """
        if not self.cache_json_path.exists():
            with open(self.cache_json_path, "w") as file_handle:
                file_handle.writelines("{}")

        with open(self.cache_json_path, "r") as file_handle:
            rdm_cache = json.load(file_handle)

        repo = BaseRepo(target_repo_location)
        commit_hash = repo.current_commit_hash
        if "__example/path/to/repo__" in rdm_cache.keys():
            rdm_cache.pop("__example/path/to/repo__")

        target_repo_location = str(self.ensure_relative_path(target_repo_location))

        if isinstance(source_repo_location, Path):
            source_repo_location = source_repo_location.as_posix()

        rdm_cache[target_repo_location] = {
            "source_repo_location": source_repo_location,
            "branch_name": source_repo_branch,
            "commit_hash": commit_hash,
        }

        with open(self.cache_json_path, "w") as file_handle:
            json.dump(rdm_cache, file_handle, indent=2)

    def ensure_relative_path(self, input_path):
        """
        Turn the input path into a relative path, relative to the repo working directory.

        :param input_path:
        :return:
        """
        if type(input_path) is str:
            input_path = Path(input_path)

        if input_path.is_absolute():
            relative_path = input_path.relative_to(self.path)
        else:
            relative_path = input_path
        return relative_path

    def verify_unchanged_cache(self):
        """
        Verify that all repos referenced in .cadet-rdm-data.json are
        in an unmodified state. Raises a RuntimeError if the commit hash has changed or if
        uncommited changes are found.

        :return:
        """

        with open(self.cache_json_path, "r") as file_handle:
            rdm_cache = json.load(file_handle)

        if "__example/path/to/repo__" in rdm_cache.keys():
            rdm_cache.pop("__example/path/to/repo__")

        for repo_location, repo_info in rdm_cache.items():
            try:
                repo = BaseRepo(repo_location)
                repo._git.clear_cache()
            except git.exc.NoSuchPathError:
                raise git.exc.NoSuchPathError(f"The imported repository at {repo_location} was not found.")

            self.verify_cache_folder_is_unchanged(repo_location, repo_info["commit_hash"])

    def verify_cache_folder_is_unchanged(self, repo_location, commit_hash):
        """
        Verify that the repo located at repo_location has no uncommited changes and that the current commit_hash
        is equal to the given commit_hash

        :param repo_location:
        :param commit_hash:
        :return:
        """
        repo = BaseRepo(repo_location)
        commit_changed = repo.current_commit_hash != commit_hash
        uncommited_changes = repo.exist_uncomitted_changes
        if commit_changed or uncommited_changes:
            raise RuntimeError(f"The contents of {repo_location} have been modified. Don't do that.")
        repo._git.clear_cache()

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
            remote_list = [str(remote.name) for remote in self._git_repo.remotes]
        else:
            remote_list = [remote]

        if local_branch == "main" or push_all:
            if push_all:
                self.checkout("main")
            for remote in remote_list:
                remote_interface = self._git_repo.remotes[remote]
                remote_interface.pull()

        for remote in remote_list:
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
        Delete the currently active branch and checkout the main branch
        :return:
        """
        previous_branch = self.active_branch.name
        if previous_branch == "main":
            return

        commit_of_current_main = str(self._git.rev_parse("main"))
        commit_of_current_branch = str(self.head.commit)
        if commit_of_current_branch == commit_of_current_main:
            print("Removing empty branch", previous_branch)
            self._git.checkout("main")
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

    def _reset_hard_to_head(self, force_entry=False):
        if not force_entry:
            proceed = wait_for_user(f'The output directory contains the following uncommitted changes:\n'
                                    f'{self.untracked_files + self.changed_files}\n'
                                    f' These will be lost if you continue\n'
                                    f'Proceed?')
        else:
            proceed = True
        if not proceed:
            raise KeyboardInterrupt
        # reset all tracked files to previous commit, -q silences output
        self._git.reset("-q", "--hard", "HEAD")
        # remove all untracked files and directories, -q silences output
        try:
            self._git.clean("-q", "-f", "-d")
        except git.exc.GitCommandError:
            recursive_chmod(self.path, S_IWRITE)
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
            dump_path = self.path
        print("Dumping conda environment.yml, this might take a moment.")
        try:
            os.system(f"conda env export > {dump_path}/conda_environment.yml")
            print("Dumping conda independent environment.yml, this might take a moment.")
            os.system(f"conda env export --from-history > {dump_path}/conda_independent_environment.yml")
        except Exception as e:
            print("Could not dump conda environment due to the following error:")
            print(e)
        print("Dumping pip requirements.txt.")
        os.system(f"pip freeze > {dump_path}/pip_requirements.txt")
        print("Dumping pip independent requirements.txt.")
        os.system(f"pip list --not-required --format freeze > {dump_path}/pip_independent_requirements.txt")

    def commit(self, message: str, add_all=True, verbosity=1):
        """
        Commit current state of the repository.

        :param message:
            Commit message
        :param add_all:
            Option to add all changed and new files to git automatically.
        :param verbosity:
            Option to choose degree of printed feedback.
        """

        if not self.exist_uncomitted_changes:
            if verbosity >= 1:
                print(f"No changes to commit in repo {self.path}")
            return

        print(f"Commiting changes to repo {self.path}")
        if add_all:
            self.add(".")

        try:
            commit_return = self._git.commit("-m", message)
            if verbosity >= 1:
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
            raise RuntimeError(f"Found uncommitted changes in the repository {self.path}.")

    def add_list_of_remotes_in_readme_file(self, repo_identifier: str, remotes_url_list: list):
        if len(remotes_url_list) > 0:
            remotes_url_list_http = [ssh_url_to_http_url(remote)
                                     for remote in remotes_url_list]
            output_link_line = " and ".join(f"[{repo_identifier}]({output_repo_remote})"
                                            for output_repo_remote in remotes_url_list_http) + "\n"

            readme_filepath = self.path / "README.md"
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
            self.add(readme_filepath)


class ProjectRepo(BaseRepo):
    def __init__(self, repository_path=None, output_folder=None,
                 search_parent_directories=True, *args, **kwargs):
        """
        Class for Project-Repositories. Handles interaction between the project repo and
        the output (i.e. results) repo.

        :param repository_path:
            Path to the root of the git repository.
        :param output_folder:
            Deprecated: Path to the root of the output repository.
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

        test_for_lfs()

        if output_folder is not None:
            print("Deprecation Warning. Setting the outputfolder manually during repo instantiation is deprecated"
                  " and will be removed in a future update.")

        if not self.data_json_path.exists():
            raise RuntimeError(f"Folder {self.path} does not appear to be a CADET-RDM repository.")

        metadata = self.load_metadata()
        self._project_uuid = metadata["project_uuid"]
        self._output_uuid = metadata["output_uuid"]
        self._output_folder = metadata["output_remotes"]["output_folder_name"]
        if not (self.path / self._output_folder).exists():
            print("Output repository was missing, cloning now.")
            self._clone_output_repo()
        self._output_repo = OutputRepo(self.path / self._output_folder)

        if metadata["cadet_rdm_version"] != cadetrdm.__version__:
            self._update_version(metadata, cadetrdm.__version__)

        self._on_context_enter_commit_hash = None
        self._is_in_context_manager = False
        self.options_hash = None

    def load_metadata(self):
        with open(self.data_json_path, "r") as handle:
            metadata = json.load(handle)
        if "output_remotes" not in metadata:
            # this enables upgrades from v0.0.23 to v0.0.24.
            output_remotes_path = self.path / "output_remotes.json"
            with open(output_remotes_path, "r") as handle:
                output_remotes = json.load(handle)
            metadata["output_remotes"] = output_remotes
        return metadata

    @property
    def output_repo(self):
        if self._output_repo is None:
            raise ValueError("The output repo has not been set yet.")
        return self._output_repo

    def _update_version(self, metadata, cadetrdm_version):
        current_version = metadata["cadet_rdm_version"]
        changes_were_made = False
        major, minor, patch = [int(x) for x in current_version.split(".")]
        version_sum = major * 1000 * 1000 + minor * 1000 + patch
        if version_sum < 9:
            changes_were_made = True
            self._convert_csv_to_tsv_if_necessary()
            self._add_jupytext_file(self.path)
        if version_sum < 24:
            changes_were_made = True
            self._expand_tsv_header()
            output_remotes_path = self.path / "output_remotes.json"
            delete_path(output_remotes_path)
            self.add(output_remotes_path)
        if version_sum < 34:
            changes_were_made = True
            self.fix_gitattributes_log_tsv()

        if changes_were_made:
            print(f"Repo version {metadata['cadet_rdm_version']} was outdated. "
                  f"Current CADET-RDM version is {cadetrdm.__version__}.\n Repo has been updated")
            metadata["cadet_rdm_version"] = cadetrdm_version
            with open(self.data_json_path, "w") as f:
                json.dump(metadata, f, indent=2)
            self.add(self.data_json_path)
            self.commit("update cadetrdm version", add_all=False)

    def fix_gitattributes_log_tsv(self):
        file = self.output_path / ".gitattributes"
        with open(file) as handle:
            lines = handle.readlines()
        lines = [line.replace("rdm-log.tsv", "log.tsv") for line in lines]
        with open(file, "w") as handle:
            handle.writelines(lines)
        self.output_repo.add(".gitattributes")
        self.output_repo.commit("Update gitattributes")

    def _clone_output_repo(self):
        metadata = self.load_metadata()
        output_remotes = metadata["output_remotes"]
        output_path = self.path / output_remotes["output_folder_name"]
        ssh_remotes = list(output_remotes["output_remotes"].values())
        http_remotes = [ssh_url_to_http_url(url) for url in ssh_remotes]
        if len(ssh_remotes + http_remotes) == 0:
            warnings.warn("No output remotes configured in .cadet-rdm-data.json")
        for output_remote in ssh_remotes + http_remotes:
            try:
                print(f"Attempting to clone {output_remote} into {output_path}")
                git.Repo.clone_from(output_remote, output_path)
            except Exception as e:
                print(e)
            else:
                break

    @staticmethod
    def _add_jupytext_file(path_root: str | Path = "."):
        jupytext_lines = ['# Pair ipynb notebooks to py:percent text notebooks', 'formats: "ipynb,py:percent"']
        write_lines_to_file(Path(path_root) / "jupytext.yml", lines=jupytext_lines, open_type="w")

    def create_remotes(self, name, namespace, url=None, username=None):
        """
        Create project in gitlab and add the projects as remotes to the project and output repositories

        :param username:
        :param url:
        :param namespace:
        :param name:
        :return:
        """
        if "github" in url:
            remote = GitHubRemote()
        else:
            remote = GitLabRemote()

        response_project = remote.create_remote(url=url, namespace=namespace, name=name, username=username)
        response_output = remote.create_remote(url=url, namespace=namespace, name=name + "_output", username=username)
        self.add_remote(response_project.ssh_url_to_repo)
        self.output_repo.add_remote(response_output.ssh_url_to_repo)
        self.push(push_all=True)

    def get_new_output_branch_name(self):
        """
        Construct a name for the new branch in the output repository.
        :return: the new branch name
        """
        project_repo_hash = str(self.head.commit)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        branch_name = "_".join([timestamp, str(self.active_branch), project_repo_hash[:7]])
        return branch_name

    def check_results_main(self):
        """
        Checkout the main branch, which contains all the log files.
        """
        self._most_recent_branch = self._output_repo.active_branch.name
        self._output_repo._git.checkout("main")

    def reload_recent_results(self):
        """
        Checkout the most recent previous branch.
        """
        self._output_repo._git.checkout(self._most_recent_branch)

    def print_output_log(self):
        self.output_repo.print_output_log()

    def fill_data_from_cadet_rdm_json(self, re_load=False):
        """
        Iterate through all references within the .cadet-rdm-data.json and
        load or re-load the data.

        :param re_load:
        If true: delete and re-load all data. If false, existing data will be left as-is.
        :return:
        """

        with open(self.cache_json_path, "r") as file_handle:
            rdm_cache = json.load(file_handle)

        if "__example/path/to/repo__" in rdm_cache.keys():
            rdm_cache.pop("__example/path/to/repo__")

        for repo_location, repo_info in rdm_cache.items():
            if os.path.exists(repo_location) and re_load is False:
                continue
            elif os.path.exists(repo_location) and re_load is True:
                delete_path(repo_location)

            if repo_info["source_repo_location"] == ".":
                self.copy_data_to_cache(branch_name=repo_info["branch_name"])
            else:
                self.import_remote_repo(
                    target_repo_location=repo_location,
                    source_repo_location=repo_info["source_repo_location"],
                    source_repo_branch=repo_info["branch_name"])

    @property
    def output_log_file(self):
        # note: if filename of "log.tsv" is changed,
        #  this also has to be changed in the gitattributes of the init repo func
        return self.output_repo.output_log_file_path

    @property
    def output_log(self):
        return self.output_repo.output_log

    def _expand_tsv_header(self):
        if not self.output_log_file.exists():
            return

        with open(self.output_log_file, "r") as f:
            lines = f.readlines()

        new_header = [
            "Output repo commit message",
            "Output repo branch",
            "Output repo commit hash",
            "Project repo commit hash",
            "Project repo folder name",
            "Project repo remotes",
            "Python sys args",
            "Tags",
            "Options hash", ]
        with open(self.output_log_file, "w") as f:
            f.writelines(["\t".join(new_header) + "\n"])
            f.writelines(lines[1:])

        self.output_repo.add(self.output_log_file)
        self.output_repo.commit("Update tsv header", add_all=False)

    def _convert_csv_to_tsv_if_necessary(self):
        """
        If not tsv log is found AND a csv log is found, convert the csv to tsv.

        :return:
        """

        if self.output_log_file.exists():
            return

        csv_filepath = self.path / self._output_folder / "log.csv"
        if not csv_filepath.exists():
            # We have just initialized the repo and neither tsv nor csv exist.
            return

        with open(csv_filepath) as csv_handle:
            csv_lines = csv_handle.readlines()

        tsv_lines = [line.replace(",", "\t") for line in csv_lines]

        with open(self.output_log_file, "w") as f:
            f.writelines(tsv_lines)

        write_lines_to_file(path=self.path / ".gitattributes",
                            lines=["rdm-log.tsv merge=union"],
                            open_type="a")

    def update_output_main_logs(self, ):
        """
        Dumps all the metadata information about the project repositories state and
        the commit hash and branch name of the ouput repository into the main branch of
        the output repository.
        """
        output_branch_name = str(self.output_repo.active_branch)

        output_repo_hash = str(self.output_repo.head.commit)
        output_commit_message = self.output_repo.active_branch.commit.message
        output_commit_message = output_commit_message.replace("\n", "; ")

        self.output_repo._git.checkout("main")

        logs_folderpath = self.output_repo.path / "run_history" / output_branch_name
        if not logs_folderpath.exists():
            os.makedirs(logs_folderpath)

        json_filepath = logs_folderpath / "metadata.json"

        meta_info_dict = {
            "Output repo commit message": output_commit_message,
            "Output repo branch": output_branch_name,
            "Output repo commit hash": output_repo_hash,
            "Project repo commit hash": str(self.head.commit),
            "Project repo folder name": self.path.name,
            "Project repo remotes": self.remote_urls,
            "Python sys args": str(sys.argv),
            "Tags": ", ".join(self.tags),
            "Options hash": self.options_hash,
        }
        tsv_header = "\t".join(meta_info_dict.keys())
        tsv_data = "\t".join([str(x) for x in meta_info_dict.values()])

        with open(json_filepath, "w") as f:
            json.dump(meta_info_dict, f, indent=2)

        if not self.output_log_file.exists():
            with open(self.output_log_file, "w") as f:
                f.write(tsv_header + "\n")
                # csv.writer(tsv_header + "\n")

        with open(self.output_log_file, "r") as f:
            existing_header = f.readline().replace("\n", "")
            if existing_header != tsv_header:
                raise ValueError("The used structure of the meta_dict doesn't match the header found in log.tsv")

        with open(self.output_log_file, "a") as f:
            f.write(tsv_data + "\n")

        self.dump_package_list(logs_folderpath)

        self.copy_code(logs_folderpath)

        self._output_repo.add(".")
        self._output_repo._git.commit("-m", f"log for '{output_commit_message}' \n"
                                            f"of branch '{output_branch_name}'")

        self._output_repo._git.checkout(output_branch_name)
        self._most_recent_branch = output_branch_name

    def copy_code(self, target_path):
        """
        Clone only the current branch of the project repo to the target_path
        and then compress it into a zip file.

        :param target_path:
        :return:
        """
        if type(target_path) is str:
            target_path = Path(target_path)

        code_tmp_folder = target_path / "git_repo"

        multi_options = ["--filter=blob:none", "--single-branch"]
        git.Repo.clone_from(self.path, code_tmp_folder, multi_options=multi_options)

        shutil.make_archive(target_path / "code", "zip", code_tmp_folder)

        delete_path(code_tmp_folder)

    def commit(self, message: str, add_all=True, verbosity=1):
        """
        Commit current state of the repository.

        :param message:
            Commit message
        :param add_all:
            Option to add all changed and new files to git automatically.
        :param verbosity:
            Option to choose degree of printed feedback.
        """
        self.update_output_remotes_json()

        super().commit(message=message, add_all=add_all, verbosity=verbosity)

    def update_output_remotes_json(self):
        output_repo_remotes = self.output_repo.remote_urls
        self.add_list_of_remotes_in_readme_file("output_repo", output_repo_remotes)

        with open(self.data_json_path, "r") as file_handle:
            metadata = json.load(file_handle)

        remotes_dict = {remote.name: str(remote.url) for remote in self.output_repo.remotes}
        metadata["output_remotes"] = {"output_folder_name": self._output_folder, "output_remotes": remotes_dict}

        with open(self.data_json_path, "w") as file_handle:
            json.dump(metadata, file_handle, indent=2)

        self.add(self.data_json_path)

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
        # ToDo: needs testing
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
            branch_name_and_path = file_path.split("_cached/")[-1]
            if os.sep not in branch_name_and_path:
                sep = "/"
            else:
                sep = os.sep
            branch_name, file_path = branch_name_and_path.split(sep, maxsplit=1)

        if self.output_repo.exist_uncomitted_changes:
            self.output_repo.stash_all_changes()
            has_stashed_changes = True
        else:
            has_stashed_changes = False

        previous_branch = self.output_repo.active_branch.name
        self.output_repo._git.checkout(branch_name)

        source_filepath = self.output_repo.path / file_path

        target_folder = self.path / (self._output_folder + "_cached") / branch_name
        os.makedirs(target_folder, exist_ok=True)

        target_filepath = target_folder / file_path
        if target_filepath.exists():
            os.chmod(target_filepath, S_IWRITE)
            os.remove(target_filepath)
        shutil.copyfile(source_filepath, target_filepath)
        os.chmod(target_filepath, S_IREAD)

        self.output_repo._git.checkout(previous_branch)
        if has_stashed_changes:
            self.output_repo.apply_stashed_changes()

        return target_filepath

    @property
    def output_path(self):
        return self.output_data()

    def output_data(self, sub_path=None):
        """
        Return an absolute path with the repo_dir/output_dir/sub_path

        :param sub_path:
        :return:
        """
        if sub_path is None:
            return self.output_repo.path.absolute()
        else:
            return self.output_repo.path.absolute() / sub_path

    def remove_cached_files(self):
        """
        Delete all previously cached results.
        """
        if (self.path / (self._output_folder + "_cached")).exists():
            delete_path(self.path / (self._output_folder + "_cached"))

    def test_for_correct_repo_setup(self):
        """
        ToDo: implement
        :return:
        """

    def enter_context(self, force=False):
        """
        Enter the tracking context. This includes:
         - Ensure no uncommitted changes in the project repository
         - Remove all uncommitted changes in the output repository
         - Clean up empty branches in the output repository
         - Create a new empty output branch in the output repository

        :return:
            The name of the newly created output branch.
        """
        if self.active_branch.name == "detached_head":
            print("Repo is in detached HEAD state. Not tracking results")
            return

        self.test_for_correct_repo_setup()
        self.test_for_uncommitted_changes()
        self._on_context_enter_commit_hash = self.current_commit_hash
        self._is_in_context_manager = True
        output_repo = self.output_repo

        # ensure that LFS is properly initialized
        os.system("git lfs install")

        if output_repo.exist_uncomitted_changes:
            output_repo._reset_hard_to_head(force_entry=force)

        output_repo.delete_active_branch_if_branch_is_empty()

        new_branch_name = self.get_new_output_branch_name()

        # update urls in main branch of output_repo
        output_repo._git.checkout("main")
        project_repo_remotes = self.remote_urls
        output_repo.add_list_of_remotes_in_readme_file("project_repo", project_repo_remotes)
        output_repo.commit("Update urls", verbosity=0)

        output_repo.prepare_new_branch(new_branch_name)
        return new_branch_name

    def copy_data_to_cache(self, branch_name=None):
        """
        Copy all existing output results into a cached folder and make it read-only.

        :param branch_name:
        optional branch name, if None, current branch is used.

        :return:
        """
        try:
            source_filepath = self.output_repo.path

            if branch_name is None:
                branch_name = self.output_repo.active_branch.name
                previous_branch = None
            else:
                previous_branch = self.output_repo.active_branch.name
                self.output_repo.checkout(branch_name)

            target_folder = self.path / (self._output_folder + "_cached") / branch_name

            shutil.copytree(source_filepath, target_folder)

            # Set all files to read only
            for filename in glob.iglob(f"{target_folder}/**/*", recursive=True):
                absolute_path = os.path.abspath(filename)
                if os.path.isdir(absolute_path):
                    continue
                os.chmod(os.path.abspath(filename), S_IREAD)

            if previous_branch is not None:
                self.output_repo.checkout(previous_branch)
        except:
            traceback.print_exc()

    def exit_context(self, message):
        """
        After running all project code, this prepares the commit of the results to the output repository. This includes
         - Ensure no uncommitted changes in the project repository
         - Stage all changes in the output repository
         - Commit all changes in the output repository with the given commit message.
         - Update the log files in the main branch of the output repository.
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
            self.update_output_main_logs()
            main_cach_path = self.path / (self._output_folder + "_cached") / "main"
            if main_cach_path.exists():
                delete_path(main_cach_path)
            self.copy_data_to_cache("main")
            # print("\n" + commit_return + "\n")
        except git.exc.GitCommandError as e:
            self.output_repo.delete_active_branch_if_branch_is_empty()
            raise e
        finally:
            # self.remove_cached_files()
            self._is_in_context_manager = False
            self._on_context_enter_commit_hash = None

    @contextlib.contextmanager
    def track_results(self, results_commit_message: str, debug=False, force=False):
        """
        Context manager to be used when running project code that produces output that should
        be tracked in the output repository.
        :param results_commit_message:
            Commit message for the commit of the output repository.
        :param debug:
            Perform calculations without tracking output.
        :param force:
            Skip confirmation and force tracking of results.
        """
        if debug:
            yield "debug"
            return

        if self.active_branch.name == "detached_head":
            print("Repo is in detached HEAD state. Not tracking results")
            yield "detached_head"
            return

        new_branch_name = self.enter_context(force=force)
        try:
            yield new_branch_name
        except Exception as e:
            self.capture_error(e)
            raise e
        else:
            self.exit_context(message=results_commit_message)

    def capture_error(self, error):
        print(traceback.format_exc())
        write_lines_to_file(self.output_path / "error.stack", traceback.format_exc().split("\n"))


class OutputRepo(BaseRepo):
    @property
    def output_log_file_path(self):
        if not self.active_branch == "main":
            self.checkout("main")
        return self.path / "log.tsv"

    @property
    def output_log(self):
        self.checkout("main")
        self._reset_hard_to_head(force_entry=True)
        return OutputLog(filepath=self.output_log_file_path)

    def print_output_log(self):
        self.checkout("main")

        output_log = self.output_log
        print(output_log)

        self.checkout(self._most_recent_branch)

    def prepare_new_branch(self, branch_name):
        """
        Prepares a new branch to receive data. This includes:
         - checking out the main branch,
         - creating a new branch from there
        This thereby produces a clear, empty directory for data, while still maintaining
        .gitignore and .gitattributes
        :param branch_name:
            Name of the new branch.
        """
        self._git.checkout("main")
        self._git.checkout('-b', branch_name)  # equivalent to $ git checkout -b %branch_name
        code_backup_path = self.path / "run_history"
        logs_path = self.path / "log.tsv"
        if code_backup_path.exists():
            try:
                # Remove previous code backup

                delete_path(code_backup_path)
            except Exception as e:
                print(e)
        if logs_path.exists():
            try:
                # Remove previous logs
                delete_path(logs_path)
            except Exception as e:
                print(e)


class JupyterInterfaceRepo(ProjectRepo):
    def commit(self, message: str, add_all=True, verbosity=1):
        """
        Commit current state of the repository.

        :param message:
            Commit message
        :param add_all:
            Option to add all changed and new files to git automatically.
        :param verbosity:
            Option to choose degree of printed feedback.
        """

        if "nbconvert_call" in sys.argv:
            print("Not committing during nbconvert.")
            return

        Notebook.save_ipynb()

        super().commit(message, add_all, verbosity)

    def commit_nb_output(self, notebook_path: str, results_commit_message: str,
                         force_rerun=True, timeout=600, conversion_formats: list = None):
        if "nbconvert_call" in sys.argv:
            return
            # This is reached in the first call of this function
        if not Path(notebook_path).is_absolute():
            notebook_path = self.path / notebook_path

        notebook = Notebook(notebook_path)

        with self.track_results(results_commit_message, force=True):
            notebook.check_and_rerun_notebook(force_rerun=force_rerun,
                                              timeout=timeout)

            # This is executed after the nbconvert call
            notebook.convert_ipynb(self.output_path, formats=conversion_formats)
            notebook.export_all_figures(self.output_path)
