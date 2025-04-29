from abc import abstractmethod
import subprocess


class ContainerAdapter:
    def __init__(self, image=None):
        self.image = image
        return

    @abstractmethod
    def run_case(self, case, command):
        return

    @staticmethod
    def _prepare_base_commands():
        # copy over git config
        git_config_list = subprocess.check_output(
            "git config --list --show-origin --global",
            shell=True
        ).decode().split("\n")
        git_config = {
            "user.name": None,
            "user.email": None,
        }
        for line in git_config_list:
            for key in git_config.keys():
                if key in line:
                    value = line.split("=")[-1]
                    # print(value)
                    git_config[key] = value

        commands_git = [f'git config --global {key} "{value}"' for key, value in git_config.items()]

        # ensure ssh in the container knows where to look for known_hosts and that .ssh/config is read-only
        command_ssh = 'cp -r /root/.ssh_host_os/. /root/.ssh && chmod 600 /root/.ssh/.'

        commands = commands_git + [command_ssh, ]
        return commands

    @staticmethod
    def _prepare_case_command(case, command, container_options_filename):
        commands = ContainerAdapter._prepare_base_commands()

        command_install = case.environment.prepare_install_instructions()
        if command_install is not None:
            commands.append(command_install)

        # pull the study from the URL into a "study" folder
        command_pull = f"rdm clone {case.project_repo.url} study"
        # cd into the "study" folder
        command_cd = "cd study"
        # checkout branch
        command_checkout = f"git checkout {case.project_repo.active_branch}"
        # run_yml main.py with the options, assuming main.py lies within a sub-folder with the same name as the study.name
        if command is None:
            command_python = f"python {case.project_repo.name}/main.py {container_options_filename}"
        else:
            command_python = command

        commands.extend([command_pull, command_cd, command_checkout, command_python])
        full_command = ' && '.join(commands)
        return full_command
