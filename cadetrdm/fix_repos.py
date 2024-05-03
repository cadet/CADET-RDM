import os
from git import Repo
import git

n_commits = 60

os.chdir(r"C:\Users\ronal\PycharmProjects\benchmarking-cadet-optimization\benchmarking-eval\tmp\puetmann2013\output")
repo = Repo(".")
repo.git.checkout("main")
commits = list(repo.iter_commits("main", max_count=n_commits + 1))
last_previous_commit = commits[-1]
commits = commits[:-1]

repo.git.checkout("main", b="patched_main")
repo.git.reset(last_previous_commit.hexsha, "--hard")

commit = commits[-1]

for commit in commits[::-1]:
    print(commit.hexsha)
    try:
        repo.git.cherry_pick(commit.hexsha, "-X", "theirs")
    except git.exc.GitCommandError as e:
        if "is a merge but no -m " in e.stderr:
            try:
                repo.git.cherry_pick(commit.hexsha, "-X", "theirs", "-m", "1")
            except git.exc.GitCommandError as e:
                if "The previous cherry-pick is now empty" in e.stderr:
                    pass

    status = repo.git.status()
    if "Changes not staged for commit:" in status:
        os.system("git lfs fsck --pointers & git add . & git commit --amend --no-edit")


if False:
    repo.git.checkout("main")
    repo.git.branch("-D", "patched_main")
    repo.git.branch("-D", "unpatched_main")


repo.git.checkout("main")
repo.git.reset("--hard", "patched_main")

os.system("git push --force-with-lease")

# print(repo.git.status())
# print(repo.git.log())

# branches = repo.git.branch("-r").split("\n")
# branches = [branch.replace("  origin/", "") for branch in branches if "origin/main" not in branch]
# remote = repo.remotes[0]


# for branch in branches:
#     repo.git.checkout(branch)
#     print(repo.git.status())
#     os.system("git lfs fsck --pointers & git add . & git commit --amend --no-edit")

# os.system("git push --all --force-with-lease")
