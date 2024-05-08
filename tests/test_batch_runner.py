import os
import time
from datetime import datetime
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
    work_dir = Path.cwd() / "batch_repos"
    if os.path.exists(work_dir):
        delete_path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    rdm_example = Study(
        work_dir / 'template',
        "git@jugit.fz-juelich.de:r.jaepel/rdm_example.git",
    )

    studies = [rdm_example]
    push = True

    DEFAULT_OPTIONS = [
        Options({
            'objective': 'single-objective',
            'optimizer_options': {
                "optimizer": "U_NSGA3",
                "pop_size": 2,
                "n_cores": 1,
                "n_max_gen": 2,
            },
            "datetime": str(datetime.now()),
            'debug': False,
            'push': push,
        }),
        Options({
            'objective': 'single-objective',
            'optimizer_options': {
                "optimizer": "U_NSGA3",
                "pop_size": 3,
                "n_cores": 1,
                "n_max_gen": 2,
            },
            "datetime": str(datetime.now()),
            'debug': False,
            'push': push,
        }),
    ]

    python_commands = []
    cases = []
    # Default cases
    for study in studies:
        for options in DEFAULT_OPTIONS:
            options.commit_message = f"Trying new things."
            if Case(study=study, options=options).has_results_for_this_run:
                continue

            local_study = Study(
                path=study.path.parent / f"{study.path.name}_{options.get_hash()[:7]}",
                url=study.url,
                name=study.name
            )
            study_path = local_study.path.absolute()
            options.dump_json_file(local_study.output_path / "options.json")
            python_commands.append(
                f"python {study_path / study.name / 'cli.py'} --options {local_study.output_path / 'options.json'}"
            )
            time.sleep(1)
            cases.append((local_study, options))

    # for local_study, options in cases:
    #     case = Case(local_study, options)
    #     case.run_study(force=False)

    # for line in python_commands:
    #     print(line)
    #     os.system(line)
