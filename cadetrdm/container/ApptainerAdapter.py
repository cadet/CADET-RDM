# import os
# import subprocess
# import tempfile
# from pathlib import Path
# import yaml
#
# from cadetrdm.container import ContainerAdapter
# from cadetrdm.batch_running import Study, Case, Options
# from cadetrdm import Environment
#
#

"""

This is a placeholder for the upcoming Apptainer Adapters

"""
# class ApptainerAdapter(ContainerAdapter):
#
#     def __init__(self):
#         pass
#
#     def run(self, yml_path):
#         with open(yml_path, "r") as stream:
#             instructions = yaml.safe_load(stream)
#
#         instructions = {key.lower(): value for key, value in instructions.items()}
#
#         study = Study(**instructions["study"], suppress_lfs_warning=True)
#         options = Options(**instructions["options"])
#         environment = Environment(**instructions["environment"])
#         case = Case(study, options, environment)
#
#         return self.run_case(case, command=instructions["command"])
#
#     def run_case(self, case: Case, command: str = None):
#         if self.image is None:
#             image = self._build_image(case)
#         else:
#             image = self.image
#
#         container_tmp_filename = "/tmp/options.json"
#         options_tmp_filename = self._dump_options(case)
#
#         full_command = self._prepare_case_command(
#             case=case,
#             command=command,
#             container_tmp_filename=container_tmp_filename
#         )
#
#         log, return_code = self._run_command(
#             container_tmp_filename=container_tmp_filename,
#             full_command=full_command,
#             image=image,
#             options_tmp_filename=options_tmp_filename
#         )
#
#         return log, return_code
#
#     def _run_command(self, container_tmp_filename, full_command, image, options_tmp_filename):
#
#         ssh_location = Path.home() / ".ssh"
#         if not ssh_location.exists():
#             raise FileNotFoundError("No ssh folder found. Please report this on GitHub/CADET/CADET-RDM")
#
#         container = self.client.containers.run_yml(
#             image=image,
#             command=full_command,
#             volumes={
#                 f"{Path.home()}/.ssh": {'bind': "/root/.ssh_host_os", 'mode': "ro"},
#                 options_tmp_filename.absolute().as_posix(): {'bind': container_tmp_filename, 'mode': 'ro'}
#             },
#             detach=True,
#             remove=False
#         )
#
#         full_log = []
#         # Step 2: Attach to the container's logs
#         for log in container.logs(stream=True):
#             full_log.append(log.decode("utf-8"))
#             print(log.decode("utf-8"), end="")
#
#         # Wait for the container to finish execution
#         result = container.wait()
#         exit_code = result["StatusCode"]
#
#         container.remove()
#
#         return full_log, exit_code
#
#     def _dump_options(self, case):
#         tmp_filename = Path("tmp/" + next(tempfile._get_candidate_names()) + ".json")
#         case.options.dump_json_file(tmp_filename)
#         return tmp_filename
#
#     def _build_image(self, case):
#         cwd = os.getcwd()
#         with open(case.project_repo.path / "Dockerfile", "rb") as dockerfile:
#             os.chdir(case.project_repo.path.as_posix())
#
#             image, logs = self.client.images.build(
#                 path=case.project_repo.path.as_posix(),
#                 # fileobj=dockerfile,  # A file object to use as the Dockerfile.
#                 tag=case.project_repo.name + ":" + case.name[:10],  # A tag to add to the final image
#                 quiet=False,  # Whether to return the status
#                 pull=True,  # Downloads any updates to the FROM image in Dockerfiles
#
#             )
#         if case.options.debug:
#             for log in logs:
#                 print(log)
#         os.chdir(cwd)
#         return image
#
#     def pull_image(self, repository, tag=None, all_tags=False, **kwargs):
#         self.image = self.client.images.pull(
#             repository=repository,
#             tag=tag,
#             all_tags=all_tags,
#             **kwargs
#         )
#
#     def _push_image(self, repository, tag=None, **kwargs):
#         self.client.images.push(
#             repository=repository,
#             tag=tag,
#             **kwargs
#         )
#
#     def _tag_image(self, image, repository, tag=None, **kwargs):
#         """
#         Tag this image into a repository. Similar to the ``docker tag``
#         command.
#
#         Args:
#             repository (str): The repository to set for the tag
#             tag (str): The tag name
#             force (bool): Force
#
#         Raises:
#             :py:class:`docker.errors.APIError`
#                 If the server returns an error.
#
#         Returns:
#             (bool): ``True`` if successful
#         """
#         image.tag(repository=repository, tag=tag, **kwargs)
#         return image
#
#     def build_and_push_image(self, case, repository, tag=None, **kwargs):
#         image = self._build_image(case)
#         image = self._tag_image(image, repository, tag, **kwargs)
#         self._push_image(repository, tag, **kwargs)
#
#     def _update_Dockerfile_with_env_reqs(self, case):
#         case.project_repo._reset_hard_to_head(force_entry=True)
#
#         dockerfile = Path(case.project_repo.path) / "Dockerfile"
#         install_command = case.environment.prepare_install_instructions()
#         if install_command is None:
#             return
#
#         with open(dockerfile, "a") as handle:
#             handle.write(f"\n{install_command}\n")
#
#     def __del__(self):
#         self.client.close()
