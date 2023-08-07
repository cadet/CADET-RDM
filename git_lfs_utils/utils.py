import os
import git


def update_package_list():
    os.system("conda env export > conda_environment.yml")
    os.system("conda env export --from-history > conda_independent_environment.yml")
    os.system("pip freeze > pip_requirements.txt")
    os.system("pip list --not-required --format freeze > pip_independent_requirements.txt")


class GitRepo(git.Repo):
    def add_all_files(self):
        if len(self.untracked_files) > 0:
            untracked_files = "\n".join(["- " + file for file in self.untracked_files])
            proceed = input(f'Found untracked files. Adding the following untracked files to git: \n{untracked_files}\n'
                            f'Proceed? Y/n \n')
            if proceed.lower() == "y" or proceed == "":
                for f in self.untracked_files:
                    self.git.add(f)
            else:
                raise KeyboardInterrupt
        changed_files = self.git.diff(None, name_only=True).split('\n')
        if "" in changed_files:
            changed_files.remove("")
        for f in changed_files:
            self.git.add(f)
        return self.untracked_files + changed_files

    def commit(self, message="bump", add_all=True, update_packages=True):
        if update_packages:
            update_package_list()
        if add_all:
            commited_files = self.add_all_files()
        commit_return = self.git.commit("-m", message)
        print("\n" + commit_return)

    def git_commit(self, message="processing bump"):
        self.git.commit("-m", message)

    def git_ammend(self, ):
        self.git.commit("--amend", "--no-edit")

    def print_status(self):
        print(self.git.status())


def get_git_repo():
    cwd = os.getcwd()
    path = cwd
    repository = None
    while repository is None:
        # step upwards in path until a git repo is found or root is reached
        try:
            repository = GitRepo(path)
        except git.exc.InvalidGitRepositoryError:
            base, directory = os.path.split(path)
            if len(directory) == 0:
                raise ValueError(f"Path {cwd} does not contain a git repository.")
            path = base
    return repository
