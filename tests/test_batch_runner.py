import os
from pathlib import Path

import pytest

from cadetrdm import Options, Study, Case, Environment, ProjectRepo, initialize_repo
from cadetrdm.io_utils import delete_path


@pytest.mark.server_api
def test_module_import():
    WORK_DIR = Path.cwd() / "tmp"
    if WORK_DIR.exists():
        delete_path(WORK_DIR)

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    rdm_example = ProjectRepo(
        WORK_DIR / 'template',
        "git@jugit.fz-juelich.de:r.jaepel/rdm_example.git",
    )

    assert hasattr(rdm_example.module, "main")
    assert hasattr(rdm_example.module, "setup_optimization_problem")


@pytest.mark.server_api
def test_run_with_non_matching_env():
    WORK_DIR = Path.cwd() / "tmp"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    rdm_example = Study(
        WORK_DIR / 'template',
        "git@jugit.fz-juelich.de:r.jaepel/rdm_example.git",
    )

    options = Options()
    options.debug = True
    options.push = False
    options.commit_message = 'Trying out new things'
    options.optimizer_options = {
        "optimizer": "U_NSGA3",
        "pop_size": 2,
        "n_cores": 2,
        "n_max_gen": 1,
    }

    matching_environment = Environment(conda_packages={
            "cadet": ">1.0.0"
        }
    )

    case = Case(project_repo=rdm_example, options=options, environment=matching_environment)
    assert case.can_run_study is True

    non_matching_environment = Environment(conda_packages={
            "cadet": "17.0.0"
        }
    )

    case = Case(project_repo=rdm_example, options=options, environment=non_matching_environment)
    assert case.can_run_study is False


@pytest.mark.server_api
def test_re_load_results():
    from pathlib import Path

    from cadetrdm import Options
    from cadetrdm import Study, Case

    WORK_DIR = Path("batch_repos") / "studies"

    batch_elution = Study(
        WORK_DIR / 'batch_elution',
        "git@jugit.fz-juelich.de:j.schmoelder/batch_elution.git",
        branch="master",
    )

    options = Options({
        "_cadet_options": {"install_path": None, "use_dll": True},
        "_temp_directory_base": {"class": "Path", "value": "/dev/shm/schmoelder/CADET-Process/tmp"},
        "_cache_directory_base": {"class": "Path", "value": "/dev/shm/schmoelder/CADET-Process/cache"},
        "objective": "single-objective",
        "optimizer_options": {"optimizer": "U_NSGA3", "n_cores": -4, "n_max_gen": 64},
        "commit_message": "single-objective_2025-01-20",
        "debug": False,
        "push": True
    })

    single_objective_case = Case(batch_elution, options, name=options.objective)
    results_path = single_objective_case.results_path
    assert results_path.exists()

@pytest.mark.server_api
def test_results_loading():
    WORK_DIR = Path.cwd() / "tmp"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    rdm_example = Study(
        WORK_DIR / 'template',
        "git@jugit.fz-juelich.de:r.jaepel/rdm_example.git",
    )

    class OptionsFixture(Options):
        def get_hash(self):
            return "za16jkxf3waxxy3mkavy3jnjn5za0b"

    case = Case(project_repo=rdm_example, options=OptionsFixture())
    assert case.has_results_for_this_run
    assert case.results_branch == '2025-02-11_17-15-38_main_d1842fd'

    simple_environment = Environment(
        conda_packages={"cadet": "4.4.0",
                        "mkl": ">=2024",
                        "tbb": ">2021.10"},
        pip_packages={'about-time': '4.2.1'}
    )
    mismatched_environment = Environment(
        conda_packages={"cadet": "4.5.0",
                        "mkl": ">2024",
                        "tbb": "<2021.10"},
        pip_packages={'about-time': '4.3.1'}
    )
    full_environment = Environment(
        conda_packages={'bzip2': '1.0.8', 'ca-certificates': '2024.2.2', 'cadet': '4.4.0', 'hdf5': '1.14.3',
                        'intel-openmp': '2024.0.0', 'krb5': '1.21.2', 'libaec': '1.1.2', 'libblas': '3.9.0',
                        'libcblas': '3.9.0', 'libcurl': '8.5.0', 'libexpat': '2.6.1', 'libffi': '3.4.2',
                        'libhwloc': '2.9.3', 'libiconv': '1.17', 'liblapack': '3.9.0', 'liblapacke': '3.9.0',
                        'libsqlite': '3.45.2', 'libssh2': '1.11.0', 'libxml2': '2.12.5', 'libzlib': '1.2.13',
                        'mkl': '2024.0.0', 'openssl': '3.2.1', 'pip': '24.0', 'pthreads-win32': '2.9.1',
                        'python': '3.11.8', 'suitesparse': '5.4.0', 'tbb': '2021.11.0', 'tbb-devel': '2021.11.0',
                        'tk': '8.6.13', 'ucrt': '10.0.22621.0', 'vc': '14.3', 'vc14_runtime': '14.38.33130',
                        'vs2015_runtime': '14.38.33130', 'wheel': '0.42.0', 'xz': '5.2.6'},
        pip_packages={'about-time': '4.2.1', 'addict': '2.3.0', 'alive-progress': '3.1.5', 'annotated-types': '0.6.0',
                      'anyio': '4.3.0', 'appdirs': '1.4.4', 'arviz': '0.17.0', 'attrs': '23.2.0', 'autograd': '1.6.2',
                      'betterproto': '2.0.0b6', 'build': '1.1.1', 'cadet-process': '0.8.0', 'cadet-python': '0.14.1',
                      'cadet-rdm': '0.0.32', 'certifi': '2024.2.2', 'cffi': '1.16.0', 'cfgv': '3.4.0',
                      'charset-normalizer': '3.3.2', 'click': '8.1.7', 'cma': '3.2.2', 'cobra': '0.29.0',
                      'colorama': '0.4.6', 'contourpy': '1.2.0', 'corner': '2.2.2', 'cryptography': '42.0.5',
                      'cycler': '0.12.1', 'depinfo': '2.2.0', 'deprecated': '1.2.14', 'dill': '0.3.8',
                      'diskcache': '5.6.3', 'distlib': '0.3.8', 'filelock': '3.13.1', 'flake8': '7.0.0',
                      'fonttools': '4.49.0', 'future': '1.0.0', 'git-lfs': '1.6', 'gitdb': '4.0.11',
                      'gitpython': '3.1.42', 'grapheme': '0.6.0', 'grpclib': '0.4.7', 'h11': '0.14.0', 'h2': '4.1.0',
                      'h5netcdf': '1.3.0', 'h5py': '3.10.0', 'hagelkorn': '1.2.3', 'hopsy': '1.4.1', 'hpack': '4.0.0',
                      'httpcore': '1.0.4', 'httpx': '0.27.0', 'hyperframe': '6.0.1', 'identify': '2.5.35',
                      'idna': '3.6', 'importlib-metadata': '7.0.2', 'importlib-resources': '6.3.0',
                      'iniconfig': '2.0.0', 'jaraco-classes': '3.3.1', 'joblib': '1.3.2', 'keyring': '24.3.1',
                      'kiwisolver': '1.4.5', 'llvmlite': '0.42.0', 'markdown-it-py': '3.0.0', 'matplotlib': '3.8.3',
                      'mcbackend': '0.5.2', 'mccabe': '0.7.0', 'mdurl': '0.1.2', 'more-itertools': '10.2.0',
                      'mpmath': '1.3.0', 'multidict': '6.0.5', 'multiprocess': '0.70.16', 'nodeenv': '1.8.0',
                      'numba': '0.59.0', 'numpy': '1.26.4', 'optlang': '1.8.1', 'packaging': '24.0', 'pandas': '2.2.1',
                      'pathos': '0.3.2', 'pillow': '10.2.0', 'platformdirs': '4.2.0', 'pluggy': '1.4.0',
                      'polyround': '0.2.11', 'pox': '0.3.4', 'ppft': '1.7.6.8', 'pre-commit': '3.6.2',
                      'pycodestyle': '2.11.1', 'pycparser': '2.21', 'pydantic': '2.6.4', 'pydantic-core': '2.16.3',
                      'pyflakes': '3.2.0', 'pygithub': '2.2.0', 'pygments': '2.17.2', 'pyjwt': '2.8.0',
                      'pymoo': '0.6.1.1', 'pynacl': '1.5.0', 'pyparsing': '3.1.2', 'pyproject-hooks': '1.0.0',
                      'pyqt5': '5.15.10', 'pyqt5-qt5': '5.15.2', 'pyqt5-sip': '12.13.0', 'pytest': '8.1.1',
                      'python-benedict': '0.33.2', 'python-dateutil': '2.9.0.post0', 'python-fsutil': '0.13.1',
                      'python-gitlab': '4.4.0', 'python-libsbml': '5.20.2', 'python-slugify': '8.0.4', 'pytz': '2024.1',
                      'pywin32-ctypes': '0.2.2', 'pyyaml': '6.0.1', 'requests': '2.31.0', 'requests-toolbelt': '1.0.0',
                      'rich': '13.7.1', 'ruamel-yaml': '0.18.6', 'ruamel-yaml-clib': '0.2.8',
                      'scikit-learn': '1.4.1.post1', 'scipy': '1.12.0', 'setuptools': '69.2.0', 'six': '1.16.0',
                      'smmap': '5.0.1', 'sniffio': '1.3.1', 'swiglpk': '5.0.10', 'sympy': '1.12', 'tabulate': '0.9.0',
                      'text-unidecode': '1.3', 'threadpoolctl': '3.3.0', 'tqdm': '4.66.2',
                      'typing-extensions': '4.10.0', 'tzdata': '2024.1', 'urllib3': '2.2.1', 'virtualenv': '20.25.1',
                      'wrapt': '1.16.0', 'xarray': '2024.2.0', 'xarray-einstats': '0.7.0', 'zipp': '3.18.0'}
    )

    case = Case(project_repo=rdm_example, options=OptionsFixture(), environment=simple_environment)
    assert case.has_results_for_this_run
    case = Case(project_repo=rdm_example, options=OptionsFixture(), environment=full_environment)
    assert case.has_results_for_this_run
    case = Case(project_repo=rdm_example, options=OptionsFixture(), environment=mismatched_environment)
    assert not case.has_results_for_this_run

    # delete_path(WORK_DIR)


def test_case_with_projectrepo():
    class OptionsFixture(Options):
        def get_hash(self):
            return "za16jkxf3waxxy3mkavy3jnjn5za0b"

    path_to_repo = Path("test_repo_batch")
    if path_to_repo.exists():
        delete_path(path_to_repo)

    initialize_repo(path_to_repo)

    try:
        os.chdir(path_to_repo)
        Case(project_repo=ProjectRepo(), options=OptionsFixture())

    finally:
        os.chdir("..")

    return


@pytest.mark.server_api
def test_results_loading_from_within():
    class OptionsFixture(Options):
        def get_hash(self):
            return "za16jkxf3waxxy3mkavy3jnjn5za0b"

    root_dir = os.getcwd()

    WORK_DIR = Path.cwd() / "tmp"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    if (WORK_DIR / 'template').exists():
        delete_path(WORK_DIR / 'template')

    rdm_example = Study(
        WORK_DIR / 'template',
        "git@jugit.fz-juelich.de:r.jaepel/rdm_example.git",
    )

    try:
        os.chdir(WORK_DIR / 'template')
        rdm_example = Study(".", "git@jugit.fz-juelich.de:r.jaepel/rdm_example.git")

        case = Case(project_repo=rdm_example, options=OptionsFixture())
        assert case.has_results_for_this_run
        assert case.results_branch == '2025-02-11_17-15-38_main_d1842fd'

        with open(rdm_example.path / "Readme.md", "a") as handle:
            handle.write("New line\n")
        rdm_example.commit("modify readme")

        case = Case(project_repo=rdm_example, options=OptionsFixture())
        assert not case.has_results_for_this_run
    finally:
        os.chdir(root_dir)


if __name__ == "__main__":
    test_results_loading_from_within()
