# from pathlib import Path
# import pytest
#
# from cadetrdm import Study, Options, Environment, Case
# from cadetrdm.container import ApptainerAdapter
#
#
# @pytest.mark.container
# def test_run_apptainer():
#     WORK_DIR = Path.cwd() / "tmp"
#     WORK_DIR.mkdir(parents=True, exist_ok=True)
#
#     rdm_example = Study(
#         WORK_DIR / 'template',
#         "git@github.com:ronald-jaepel/rdm_testing_template.git",
#         suppress_lfs_warning=True
#     )
#
#     options = Options()
#     options.debug = False
#     options.push = False
#     options.commit_message = 'Trying out new things'
#     options.optimizer_options = {
#         "optimizer": "U_NSGA3",
#         "pop_size": 2,
#         "n_cores": 2,
#         "n_max_gen": 1,
#     }
#
#     matching_environment = Environment(
#         pip_packages={
#             "cadet-rdm": "git+https://github.com/cadet/CADET-RDM.git@3e073dd85c5e54d95422c0cdcc1190d80da9e138"
#         }
#     )
#
#     case = Case(study=rdm_example, options=options, environment=matching_environment)
#     docker_adapter = ApptainerAdapter()
#     has_run_study = case.run_study(container_adapter=docker_adapter, force=True)
#     assert has_run_study
#
#     options.optimizer_options = {
#         "optimizer": "NOT_AN_OPTIMIZER",
#         "pop_size": 2,
#         "n_cores": 2,
#         "n_max_gen": 1,
#     }
#
#     case = Case(study=rdm_example, options=options, environment=matching_environment)
#     docker_adapter = ApptainerAdapter()
#     has_run_study = case.run_study(container_adapter=docker_adapter, force=True)
#     assert not has_run_study
#
#
# @pytest.mark.container
# def test_dockered_from_yml():
#     docker_adapter = ApptainerAdapter()
#     has_run_study = docker_adapter.run((Path(__file__).parent.resolve() / "case.yml").as_posix())
#     assert has_run_study
