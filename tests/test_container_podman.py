import os
from pathlib import Path
import pytest

from cadetrdm import Options, Environment, Case, ProjectRepo
from cadetrdm.container import PodmanAdapter

IMAGE_NAME = "ghcr.io/ronald-jaepel/cadet-rdm-jupyter:latest"


@pytest.mark.container
def test_run_in_podman():
    # You need to install passt on your system and add it to the path
    # os.environ["PATH"] += os.pathsep + "/home/bin/passt"
    WORK_DIR = Path.cwd() / "tmp"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    rdm_example = ProjectRepo(
        path=WORK_DIR / 'template',
        url="git@github.com:ronald-jaepel/rdm_testing_template.git",
        branch="main",
        suppress_lfs_warning=True
    )

    options = Options()
    options.debug = False
    options.push = False
    options.commit_message = 'Trying out new things'
    options.optimizer_options = {
        "optimizer": "U_NSGA3",
        "pop_size": 2,
        "n_cores": 2,
        "n_max_gen": 1,
    }

    matching_environment = Environment(
        conda_packages={
            "libsqlite": "==3.48.0"
        },
        # pip_packages={
        #     "cadet-rdm": "git+https://github.com/cadet/CADET-RDM.git@feature/container_interfaces"
        # }
    )

    case = Case(project_repo=rdm_example, options=options, environment=matching_environment)
    podman_adapter = PodmanAdapter()
    podman_adapter.image = IMAGE_NAME
    has_run_study = case.run_study(
        container_adapter=podman_adapter,
        force=True,
        # command=None  # eg: "python src/test_cadet_core/verify_cadet-core.py"
    )
    assert has_run_study

    options.optimizer_options = {
        "optimizer": "NOT_AN_OPTIMIZER",
        "pop_size": 2,
        "n_cores": 2,
        "n_max_gen": 1,
    }

    case = Case(project_repo=rdm_example, options=options, environment=matching_environment)
    podman_adapter = PodmanAdapter()
    podman_adapter.image = IMAGE_NAME
    has_run_study = case.run_study(container_adapter=podman_adapter, force=True)
    assert not has_run_study


@pytest.mark.slow
@pytest.mark.container
def test_pytest_in_podman():
    # You need to install passt on your system and add it to the path
    # os.environ["PATH"] += os.pathsep + "/home/bin/passt"
    WORK_DIR = Path.cwd() / "tmp"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    podman_adapter = PodmanAdapter()
    podman_adapter.image = IMAGE_NAME
    log, returncode = podman_adapter.run(
        "git clone git@github.com:cadet/CADET-RDM.git study && "
        "cd study && "
        "pytest tests -m 'not server_api and not docker and not slow'",

    )
    print(log)
    assert returncode == 0


@pytest.mark.container
def test_dockered_from_yml():
    podman_adapter = PodmanAdapter()
    podman_adapter.image = IMAGE_NAME
    has_run_study = podman_adapter.run_yml((Path(__file__).parent.resolve() / "case.yml").as_posix())
    assert has_run_study
