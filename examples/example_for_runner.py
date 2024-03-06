from pathlib import Path

from cadetrdm import Options
from cadetrdm.batch_runner import Study, Case

if __name__ == '__main__':

    WORK_DIR = Path.cwd() / "tmp"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    puetmann2013 = Study(
        WORK_DIR / 'puetmann2013',
        "git@jugit.fz-juelich.de:r.jaepel/puetmann2013.git",
    )

    studies = [
        puetmann2013,
    ]

    force = False
    debug = False
    push = False

    DEFAULT_OPTIMIZER_OPTIONS = {
        "optimizer": "U_NSGA3",
        "pop_size": 3,
        "n_cores": 3,
        "n_max_gen": 2,
    }

    DEFAULT_CASES = {
        'single-objective': {
            'optimizer_options': DEFAULT_OPTIMIZER_OPTIONS,
        },
        'single-objective-longer': {
            'optimizer_options': {
                "optimizer": "U_NSGA3",
                "pop_size": 6,
                "n_cores": 6,
                "n_max_gen": 2,
            }
        },
    }

    # Default cases
    for study in studies:
        for case, options in DEFAULT_CASES.items():
            options = Options(options)
            options.case = case
            options.commit_message = f"Test run {case}"
            options.debug = False
            case = Case(case, study, options)
            case.run_study(force=force)

