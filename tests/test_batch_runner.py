import os
from pathlib import Path

import pytest

from cadetrdm import Options, Case, Environment, ProjectRepo, initialize_repo
from cadetrdm.io_utils import delete_path

TEMPLATE_URL = "https://github.com/cadet/RDM-Testing-Template.git"
RESULTS_BRANCH = "2026-10-05_12-49-15_main_64f656c"


class OptionsFixture(Options):
    """Options matching the result stored in cadet/RDM-Testing-Template-Output."""

    def get_hash(self):
        return "58m9wdx60fgbpy8r7tq293kmdmx3j5tz"


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def clone_template():
    return ProjectRepo(Path.cwd() / "template", url=TEMPLATE_URL)


def test_module_import():
    template = clone_template()

    assert hasattr(template.module, "main")
    assert hasattr(template.module, "setup_optimization_problem")


def test_run_with_non_matching_env():
    initialize_repo("test_repo_env")
    project_repo = ProjectRepo("test_repo_env")
    current_environment = Environment(conda_packages={"cadet": "5.0.0"})

    matching_environment = Environment(conda_packages={"cadet": ">1.0.0"})
    case = Case(project_repo=project_repo, options=Options(), environment=matching_environment)
    case._current_environment = current_environment
    assert case.can_run_study is True

    non_matching_environment = Environment(conda_packages={"cadet": "17.0.0"})
    case = Case(project_repo=project_repo, options=Options(), environment=non_matching_environment)
    case._current_environment = current_environment
    assert case.can_run_study is False


def test_re_load_results():
    case = Case(project_repo=clone_template(), options=OptionsFixture())

    assert case.results_branch == RESULTS_BRANCH
    assert case.results_path.exists()


def test_results_loading():
    template = clone_template()

    case = Case(project_repo=template, options=OptionsFixture())
    assert case.has_results_for_this_run
    assert case.results_branch == RESULTS_BRANCH

    simple_environment = Environment(
        conda_packages={"python": "3.12.14"},
        pip_packages={"cadet-process": "0.12.0"},
    )
    range_environment = Environment(
        conda_packages={"python": ">=3.12"},
        pip_packages={"cadet-process": ">=0.12.0", "cadet-rdm": "~1.1.2", "numpy": ">=2.0"},
    )
    mismatched_environment = Environment(
        conda_packages={"python": "3.11.8"},
        pip_packages={"cadet-process": "0.11.0"},
    )

    case = Case(project_repo=template, options=OptionsFixture(), environment=simple_environment)
    assert case.has_results_for_this_run
    case = Case(project_repo=template, options=OptionsFixture(), environment=range_environment)
    assert case.has_results_for_this_run
    case = Case(project_repo=template, options=OptionsFixture(), environment=mismatched_environment)
    assert not case.has_results_for_this_run


def test_case_with_projectrepo():
    class OptionsFixture(Options):
        def get_hash(self):
            return "4rhaw644xny9e2f75ht8rw1yambyqz7w"

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


def test_results_loading_from_within():
    root_dir = os.getcwd()
    clone_template()

    try:
        os.chdir("template")
        template = ProjectRepo(".", package_dir="template")

        case = Case(project_repo=template, options=OptionsFixture())
        path = case.run_study()

        expected_path = Path(f"./output_cached/{RESULTS_BRANCH}").absolute()
        assert path == expected_path
        assert case.results_path == expected_path
        assert case.results_branch == RESULTS_BRANCH

        with open(template.path / "README.md", "a") as handle:
            handle.write("New line\n")
        template.commit("modify readme")

        case = Case(project_repo=template, options=OptionsFixture())
        assert not case.has_results_for_this_run
    finally:
        os.chdir(root_dir)
