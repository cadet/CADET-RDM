import os
import subprocess
import tempfile
from pathlib import Path

import yaml

from cadetrdm.container import ContainerAdapter
from cadetrdm.batch_running import Case
from cadetrdm import Environment, ProjectRepo, Options


class PodmanAdapter(ContainerAdapter):

    def run(self, command, mounts=None):
        commands = self._prepare_base_commands()
        commands.append(command)
        full_command = " && ".join(commands)

        log, return_code = self._run_command(
            full_command=full_command,
            image=self.image,
            mounts=mounts,
        )

        return log, return_code

    def run_yml(self, yml_path):
        with open(yml_path, "r") as stream:
            instructions = yaml.safe_load(stream)

        instructions = {key.lower(): value for key, value in instructions.items()}

        project_repo = ProjectRepo(**instructions["projectrepo"], suppress_lfs_warning=True)
        options = Options(**instructions["options"])
        environment = Environment(**instructions["environment"])
        case = Case(project_repo, options, environment)

        return self.run_case(case=case, command=instructions["command"])

    def run_case(self, case: Case, command: str = None):
        if self.image is None:
            raise ValueError("Please first specify an image name for the ContainerAdapter to use")

        container_tmp_filename = "/tmp/options.json"
        options_tmp_filename = self._dump_options(case)

        full_command = self._prepare_case_command(
            case=case,
            command=command,
            container_options_filename=container_tmp_filename
        )

        log, return_code = self._run_command(
            full_command=full_command,
            image=self.image,
            mounts={options_tmp_filename: container_tmp_filename},
        )
        return log, return_code

    def _run_command(self, full_command, image, mounts=None):
        """

        :param full_command:
        :param image:
        :param mounts: Dictionary mapping host paths to container paths
        :return:
        """

        ssh_location = Path.home() / ".ssh"
        if not ssh_location.exists():
            raise FileNotFoundError("No ssh folder found. Please report this on GitHub/CADET/CADET-RDM")

        full_command = full_command.replace('"', "'")

        volume_mounts = ""
        if mounts is None:
            mounts = {}
        for host_path, container_path in mounts.items():
            volume_mounts += f'-v {host_path.absolute().as_posix()}:{container_path}:ro '

        podman_command = (
            f'podman run '
            '--rm '  # remove container after run_yml (to keep space usage low)
            f'-v {ssh_location}:/root/.ssh_host_os:ro '  # mount ssh folder for the container to access
            f'{volume_mounts}'  # mount options file
            f'{image} '  # specify image name
            f'bash -c "{full_command}"'  # run_yml command in bash shell
        )

        result = subprocess.run(podman_command, shell=True, capture_output=True)

        full_log = result.stdout.decode() + result.stderr.decode()
        exit_code = result.returncode
        print(full_log)
        print(f"RETURN CODE: {exit_code}")

        return full_log, exit_code

    def _dump_options(self, case):
        if not Path("tmp").exists():
            os.makedirs("tmp")
        tmp_filename = Path("tmp/" + next(tempfile._get_candidate_names()) + ".json")
        case.options.dump_json_file(tmp_filename)
        return tmp_filename

    # def _build_image(self, case):
    #     raise NotImplementedError
    #
    # def _push_image(self, repository, tag=None, **kwargs):
    #     raise NotImplementedError
    #
    # def _tag_image(self, image, repository, tag=None, **kwargs):
    #     """
    #     Tag this image into a repository. Similar to the ``docker tag``
    #     command.
    #
    #     Args:
    #         repository (str): The repository to set for the tag
    #         tag (str): The tag name
    #         force (bool): Force
    #
    #     Raises:
    #         :py:class:`docker.errors.APIError`
    #             If the server returns an error.
    #
    #     Returns:
    #         (bool): ``True`` if successful
    #     """
    #     raise NotImplementedError
    #
    # def build_and_push_image(self, case, repository, tag=None, **kwargs):
    #     image = self._build_image(case)
    #     image = self._tag_image(image, repository, tag, **kwargs)
    #     self._push_image(repository, tag, **kwargs)
