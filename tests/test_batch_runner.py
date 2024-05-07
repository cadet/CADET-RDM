from pathlib import Path

import pytest

from cadetrdm import Options
from cadetrdm.batch_runner import Study, Case
from cadetrdm.io_utils import delete_path


@pytest.mark.server_api
def test_module_import():
    WORK_DIR = Path.cwd() / "tmp"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    rdm_example = Study(
        WORK_DIR / 'template',
        "git@jugit.fz-juelich.de:r.jaepel/rdm_example.git",
    )

    assert hasattr(rdm_example.module, "main")
    assert hasattr(rdm_example.module, "setup_optimization_problem")

    delete_path(WORK_DIR)


@pytest.mark.server_api
def test_parallel_runner():
    WORK_DIR = Path.cwd() / "tmp"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    rdm_example = Study(
        WORK_DIR / 'template',
        "git@jugit.fz-juelich.de:r.jaepel/rdm_example.git",
    )

    studies = [rdm_example]

    DEFAULT_OPTIONS = [
        Options({
            'objective': 'single-objective',
            'optimizer_options': {
                "optimizer": "U_NSGA3",
                "pop_size": 2,
                "n_cores": 1,
                "n_max_gen": 2,
            },
            'debug': False,
            'push': False,
        }),
        # Options({
        #     'objective': 'single-objective',
        #     'optimizer_options': {
        #         "optimizer": "U_NSGA3",
        #         "pop_size": 20,
        #         "n_cores": 10,
        #         "n_max_gen": 3,
        #     },
        #     'debug': False,
        #     'push': False,
        # }),
    ]

    # Default cases
    for study in studies:
        for options in DEFAULT_OPTIONS:
            options.commit_message = f"Trying new things."

            case = Case(study, options)
            case.run_study(force=False)
            print(case.results_branch)
            print(case.results_path)
