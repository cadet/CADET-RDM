from pathlib import Path
import os

import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

from cadetrdm import initialize_repo
from cadetrdm.io_utils import delete_path
from cadetrdm import ProjectRepo

repo_path = Path("demonstration_repo")
if repo_path.exists():
    delete_path(repo_path)

initialize_repo(repo_path)

os.chdir(repo_path)

repo = ProjectRepo(".")

repo.add_filetype_to_lfs("*.tsv")

# repo.add_remote("git@jugit.fz-juelich.de:r.jaepel/API_test_project.git")
# repo.output_repo.add_remote("git@jugit.fz-juelich.de:r.jaepel/API_test_project_output.git")

with open("generate_data.py", "w") as handle:
    handle.writelines(["import numpy\n", "# do stuff"])

repo.commit("Add code to generate example data")


def hidden_function(x):
    y = (x / 2 - 0.2) ** 2 + np.sin(x * 30) * 0.05 + np.random.random(x.size) * 0.01
    return y


with repo.track_results(results_commit_message="Generate example data"):
    import numpy as np
    from scipy import stats
    import matplotlib.pyplot as plt

    x = np.linspace(0, 1, 100)
    y = hidden_function(x)
    plt.figure()
    plt.scatter(x, y)
    np.savetxt(repo.output_path / "data.tsv", np.stack([x, y]).T, delimiter="\t")

output_branch = repo.output_repo.active_branch

with open("analyse_data.py", "w") as handle:
    handle.writelines(["import numpy\n", "# do other stuff"])

repo.commit("Add code to analyse data")

with repo.track_results(results_commit_message="Do linear regression"):
    data_path = repo.input_data(output_branch)
    geyser_data = np.loadtxt(data_path / "data.tsv", skiprows=1, delimiter="\t")
    x, y = geyser_data[:, 0], geyser_data[:, 1]

    res = stats.linregress(x, y)
    x_extrapolate = np.linspace(x.min(), x.max(), 100)
    plt.figure()
    plt.scatter(x, y, label="data")
    plt.plot(x_extrapolate, res.intercept + res.slope * x_extrapolate, ":", color='black', label='linear regression')
    plt.text(0.5, (y.min() + y.max()) / 2, f"R² = {np.round(res.rvalue ** 2, 3)}")
    plt.legend()

    plt.savefig(repo.output_path / "scatterplot.png")
    with open(repo.output_path / "model_performance.txt", "w") as handle:
        handle.write(str(res))

with open("analyse_data_GP.py", "w") as handle:
    handle.writelines(["import sklearn\n", "# do more stuff"])

repo.commit("Change model from linear to GPR")

with repo.track_results(results_commit_message="Do Gaussian Process regression"):
    data_path = repo.input_data(output_branch)

    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RationalQuadratic, ExpSineSquared, RBF

    geyser_data = np.loadtxt(data_path / "data.tsv", skiprows=1, delimiter="\t")
    x, y = geyser_data[:, 0], geyser_data[:, 1]

    gp = GaussianProcessRegressor(kernel=RBF(length_scale_bounds=(10, 20)), alpha=1e-6)
    # gp.kernel_
    gp.fit(x.reshape(-1, 1), y.reshape(-1, 1))
    x_extended = np.linspace(x.min(), x.max() + 0.5, 1000)
    # x_extended = np.linspace(x.min()-2, x.max()+2, 1000)
    mean, std = gp.predict(x_extended.reshape(-1, 1), return_std=True)
    std *= 1e2
    plt.figure()
    plt.scatter(x, y, label="data")
    plt.plot(x_extended, mean, ":", color='green', label='linear regression')
    plt.fill_between(x_extended, mean - std, mean + std, color="green", alpha=0.2, zorder=-10)
    # plt.text(0.5, 0.5, f"R² = {np.round(res.rvalue ** 2, 3)}")
    plt.legend()

    plt.savefig(repo.output_path / "scatterplot.png")
    with open(repo.output_path / "model_performance.txt", "w") as handle:
        handle.write(str(res))

with open("analyse_data_GP.py", "w") as handle:
    handle.writelines(["import sklearn\n", "# do more other stuff"])

repo.commit("Change GPR model parameters")

with repo.track_results(results_commit_message="Adapt GP regression"):
    data_path = repo.input_data(output_branch)

    geyser_data = np.loadtxt(data_path / "data.tsv", skiprows=1, delimiter="\t")
    x, y = geyser_data[:, 0], geyser_data[:, 1]

    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RationalQuadratic, ExpSineSquared, ConstantKernel, RBF

    gp = GaussianProcessRegressor(
        kernel=RBF(length_scale_bounds=(10, 20)) + ExpSineSquared(length_scale_bounds=(10, 20)) * ConstantKernel(),
        alpha=1e-6,
        normalize_y=True)
    gp.fit(x.reshape(-1, 1), y.reshape(-1, 1))
    x_extended = np.linspace(x.min(), x.max() * 2, 1000)
    mean, std = gp.predict(x_extended.reshape(-1, 1), return_std=True)
    std *= 1e2
    plt.figure()
    plt.scatter(x, y, label="data")
    plt.plot(x_extended, mean, ":", color='green', label='GP regression')
    plt.fill_between(x_extended, mean - std, mean + std, color="green", alpha=0.2, zorder=-10)
    plt.legend()

    plt.savefig(repo.output_path / "scatterplot.png")
    with open(repo.output_path / "model_performance.txt", "w") as handle:
        handle.write(str(res))

with repo.track_results(results_commit_message="Adapt GP regression again"):
    data_path = repo.input_data(output_branch)

    geyser_data = np.loadtxt(data_path / "data.tsv", skiprows=1, delimiter="\t")
    x, y = geyser_data[:, 0], geyser_data[:, 1]

    gp = GaussianProcessRegressor(
        kernel=RBF(length_scale_bounds=(10, 20)) + ExpSineSquared(length_scale_bounds=(10, 20)) * ConstantKernel(),
        alpha=1e-6,
        normalize_y=True)
    gp.fit(x.reshape(-1, 1), y.reshape(-1, 1))
    x_extended = np.linspace(x.min(), x.max() * 2, 1000)
    mean, std = gp.predict(x_extended.reshape(-1, 1), return_std=True)
    std *= 1e2
    plt.figure()
    plt.scatter(x, y, label="data")
    plt.plot(x_extended, mean, ":", color='green', label='GP regression')
    plt.fill_between(x_extended, mean - std, mean + std, color="green", alpha=0.2, zorder=-10)
    plt.legend()

    plt.savefig(repo.output_path / "scatterplot.png")
    with open(repo.output_path / "model_performance.txt", "w") as handle:
        handle.write(str(res))

# repo.push()
