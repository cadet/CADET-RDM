import os

from git import Repo

from batch_runner import Options

n_commits = 60

os.chdir(
    r"C:\Users\ronal\PycharmProjects\benchmarking\tmp\puetmann2013\output"
)
repo = Repo(".")
repo.git.checkout("main")

filepath = "log.tsv"
with open(filepath) as handle:
    lines = handle.readlines()
lines = [line.replace("\n", "").split("\t") for line in lines]

# branches = repo.git.branch("-r").split("\n")
# branches = [branch.replace("  origin/", "") for branch in branches if "origin/main" not in branch]
# remote = repo.remotes[0]

all_options = {}
for line in lines[1:]:
    branch = line[1]
    repo.git.checkout(branch)
    if os.path.exists("options.json"):
        options = Options.load_json_file("options.json")
        try:
            options.pop("study_options")
        except:
            pass
        all_options[branch] = options
        print(line[-1], options.get_hash())
        line[-1] = options.get_hash()
    status = repo.git.status()
    if "Changes not staged for commit:" in status:
        os.system("git lfs fsck --pointers & git add . & git commit --amend --no-edit")

repo.git.checkout("main")
lines = ["\t".join(line) for line in lines]

with open(filepath, "w") as handle:
    handle.writelines("\n".join(lines))

# os.system("git add . & git commit --amend --no-edit")
os.system('git add . & git commit -m "remove study-options"')
