from pathlib import Path
import pytest

from cadetrdm import Study, Options, Environment, Case
from cadetrdm.docker import DockerAdapter


@pytest.mark.docker
def test_run_dockered():
    WORK_DIR = Path.cwd() / "tmp"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    rdm_example = Study(
        WORK_DIR / 'template',
        "git@github.com:ronald-jaepel/rdm_testing_template.git",
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
        pip_packages={
            "cadet-rdm": "git+https://github.com/cadet/CADET-RDM.git@3e073dd85c5e54d95422c0cdcc1190d80da9e138"
        }
    )

    case = Case(study=rdm_example, options=options, environment=matching_environment)
    docker_adapter = DockerAdapter()
    has_run_study = case.run_study(container_adapter=docker_adapter, force=True)
    assert has_run_study
