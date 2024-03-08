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

    clr = Study(
        WORK_DIR / 'clr',
        "git@jugit.fz-juelich.de:j.schmoelder/clr.git",
        branch="adapt_to_cadetrdm_runner"
    )

    flip_flow = Study(
        WORK_DIR / 'flip_flow',
        "git@jugit.fz-juelich.de:j.schmoelder/flip_flow.git",
        branch="adapt_to_cadetrdm_runner"
    )

    serial_columns = Study(
        WORK_DIR / 'serial_columns',
        "git@jugit.fz-juelich.de:j.schmoelder/serial_columns.git",
        # branch="adapt_to_cadetrdm_runner"
    )

    smb = Study(
        WORK_DIR / 'smb',
        "git@jugit.fz-juelich.de:j.schmoelder/smb.git",
        # branch="adapt_to_cadetrdm_runner"
    )

    studies = [
        # puetmann2013,
        # clr,
        # flip_flow,
        # serial_columns,
        smb,
    ]

    force = False
    debug = False
    push = False

    DEFAULT_UNSGA_OPTIMIZER_OPTIONS = {
        "optimizer": "U_NSGA3",
        "pop_size": 3,
        "n_cores": 3,
        "n_max_gen": 2,
    }
    # DEFAULT_AX_OPTIMIZER_OPTIONS = {
    #     "optimizer": "AX",
    #     "pop_size": 3,
    #     "n_cores": 3,
    #     "n_max_gen": 2,
    # }
    # DEFAULT_TRUST_OPTIMIZER_OPTIONS = {
    #     "optimizer": "AX",
    #     "pop_size": 3,
    #     "n_cores": 3,
    #     "n_max_gen": 2,
    # }

    DEFAULT_SINGLE_OBJECTIVE = {
        "purity_required": None,
        "ranking": None,
    }

    cases = {
        'single-objective': {
            'optimizer_options': DEFAULT_UNSGA_OPTIMIZER_OPTIONS,
            'case_options': DEFAULT_SINGLE_OBJECTIVE,
        },
        # 'single-objective-ax': {
        #     'case_options': DEFAULT_SINGLE_OBJECTIVE,
        #     'optimizer_options': DEFAULT_AX_OPTIMIZER_OPTIONS,
        # },
        # 'single-objective-trust': {
        #     'case_options': DEFAULT_SINGLE_OBJECTIVE,
        #     'optimizer_options': DEFAULT_TRUST_OPTIMIZER_OPTIONS,
        # }
    }

    # Default cases
    for study in studies:
        for case, options in cases.items():
            options = Options(options)
            options.case = case
            options.commit_message = f"Test run {case}"
            options.debug = False
            case = Case(case, study, options)
            case.run_study(force=force)