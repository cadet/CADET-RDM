import io
import re
from typing import Self, List
from typing import Dict as DictType
import subprocess

import yaml
from semantic_version import Version, SimpleSpec


class Environment:

    def __init__(self, *args, conda_packages: DictType[str, str] = None, pip_packages: DictType[str, str] = None,
                 name: str = None, channels: List[str] = None):
        if args:
            raise TypeError(
                "Environment.__init__() does not take positional arguments. "
                "Please specify conda_packages and/or pip_packages."
            )
        self.conda_packages = conda_packages
        self.pip_packages = pip_packages
        self.packages = dict()
        if conda_packages:
            self.packages.update(conda_packages)
        if pip_packages:
            self.packages.update(pip_packages)

        self.name = name
        self.channels = channels

    @classmethod
    def from_yml(cls, yml_path):
        """
        Create an Environment object from a YAML file.

        :param yml_path:
        :return:
        """
        with open(yml_path) as handle:
            yml_string = "".join(handle.readlines())

        instance = cls.from_yml_string(yml_string)
        return instance

    @classmethod
    def from_yml_string(cls, yml_string):
        """
        Creates an Environment object from a YAML string.

        :param yml_string:
        :return:
        """

        # Remove special formatting characters from the string
        ansi_escape_pattern = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
        yml_string = re.sub(ansi_escape_pattern, "", yml_string)

        packages = yaml.safe_load(yml_string)

        instance = cls()

        # If for some reason the environment.yml is empty, return an empty instance
        if packages is None:
            return instance

        instance.name = packages["name"]
        instance.channels = packages["channels"]

        conda_packages = packages["dependencies"]
        conda_packages = {line.split("=")[0]: line.split("=")[1] for line in conda_packages if isinstance(line, str)}
        instance.packages.update(conda_packages)
        instance.conda_packages = conda_packages

        if isinstance(packages["dependencies"][-1], dict):
            pip_packages = packages["dependencies"][-1]["pip"]
            pip_packages = {line.split("==")[0]: line.split("==")[1] for line in pip_packages}
            instance.packages.update(pip_packages)
            instance.pip_packages = pip_packages

        return instance

    def to_yml(self, handle):
        """
        Create an environment.yml file from an Environment instance.

        :param handle:
        :return:
        """
        yml_dict = self._to_yml_dict()

        yaml.safe_dump(yml_dict, handle)

    def _to_yml_dict(self):
        """
        Create an environment.yml type yml dict from an Environment instance.

        :return: yml dict
        """
        dependency_list = []
        if self.conda_packages is not None:
            for package, spec in self.conda_packages.items():
                if "git+" in spec:
                    raise ValueError(f"Conda can not use git+ dependencies for {package} {spec}")
                elif ">" in spec or "<" in spec or "=" in spec:
                    dependency_list.append(f"{package}{spec}")
                else:
                    dependency_list.append(f"{package}={spec}")

        pip_list = []
        if self.pip_packages is not None:
            for package, spec in self.pip_packages.items():
                if "git+" in spec:
                    pip_list.append(spec)
                elif ">" in spec or "<" in spec or "=" in spec:
                    pip_list.append(f"{package}{spec}")
                else:
                    pip_list.append(f"{package}=={spec}")

            dependency_list.append({"pip": pip_list})

        yml_dict = {
            "name": self.name,
            "channels": self.channels,
            "dependencies": dependency_list,
        }
        return yml_dict

    def update(self, environment: Self):
        if environment.name is not None:
            self.name = environment.name
        if environment.channels is not None:
            self.channels = environment.channels
        self.conda_packages.update(environment.conda_packages)
        self.pip_packages.update(environment.pip_packages)

    def package_version(self, package):
        if package not in self.packages:
            return None

        return self.packages[package]

    def fulfils(self, package, version):
        """
        Checks if the installed version of a package matches the specified version.

        Args:
            package (str): The name of the package to check.
            version (str): The version or specification string to match against.

        Returns:
            bool: True if the installed package version matches the specified version, False otherwise.

        Examples:
            check_package_version("conda", ">=0.1.1") -> true if larger or equal
            check_package_version("conda", "~0.1.1") -> true if approximately equal (tolerant of pre-release suffixes)
            check_package_version("conda", "0.1.1") -> true if exactly equal (must match pre-release suffixes)

        Uses semantic versioning to compare the versions.
        """

        installed_version = self.package_version(package)
        if installed_version is None:
            return False

        if "git+" in installed_version:
            return False

        # Use .coerce instead of .parse to ensure non-standard version strings are converted.
        # Rules are:
        #   - If no minor or patch component, and partial is False, replace them with zeroes
        #   - Any character outside of a-zA-Z0-9.+- is replaced with a -
        #   - If more than 3 dot-separated numerical components,
        #       everything from the fourth component belongs to the build part
        #   - Any extra + in the build part will be replaced with dots
        installed_version = Version.coerce(installed_version)

        try:
            spec = SimpleSpec(version)
        except ValueError as e:
            spec = SimpleSpec(str(Version.coerce(version)))
            print(f"Warning: {e} when processing {package}={version}. Using {str(Version.coerce(version))} instead.")

        match = spec.match(installed_version)

        return match

    def fulfils_environment(self, environment: Self):
        """
        Checks if this environment fulfils the requirements in a given environment.

        :param environment:
            Instance of Environment class, with requirements as key: value pairs.
        :return:
        """

        if environment is None:
            return True

        mismatches = []

        for package, version in environment.packages.items():
            try:
                if not self.fulfils(package, version):
                    mismatches.append((package, version, self.package_version(package)))
            except ValueError:
                mismatches.append((package, version, self.package_version(package)))

        if mismatches:
            for package, version, existing_version in mismatches:
                print(f"Package {package}: {existing_version} does not fulfil requirements: {version}")
            return False

        return True

    def prepare_install_instructions(self):

        conda_command = ""
        pip_command = ""

        if self.conda_packages is not None:
            conda_command = "conda install -y"
            for package, spec in self.conda_packages.items():
                if "git+" in spec:
                    raise ValueError(f"Conda can not use git+ dependencies for {package} {spec}")
                elif "~" in spec:
                    conda_command += f" {package}={spec.replace('~', '').replace('=', '')}"
                elif ">" in spec or "<" in spec or "=" in spec:
                    conda_command += f" {package}{spec}"
                else:
                    conda_command += f" {package}={spec}"

        if self.pip_packages is not None:
            pip_command = "pip install"
            pip_reinstall_command = "pip install --force-reinstall --no-deps"
            reinstall_necessary = False
            for package, spec in self.pip_packages.items():
                if "git+" in spec:
                    pip_command += f" '{spec}'"
                    pip_reinstall_command += f" '{spec}' "
                    reinstall_necessary = True
                elif "~" in spec:
                    pip_command += f" '{package}={spec.replace('~', '').replace('=', '')}'"
                elif ">" in spec or "<" in spec or "=" in spec:
                    pip_command += f" '{package}{spec}'"
                else:
                    pip_command += f" '{package}=={spec}'"
            if reinstall_necessary:
                pip_command = pip_command + " && " + pip_reinstall_command

        if conda_command and pip_command:
            install_instructions = conda_command + " && " + pip_command
            return install_instructions
        elif conda_command:
            return conda_command
        elif pip_command:
            return pip_command
        else:
            return None

    def __repr__(self):
        return (f"Environment("
                f"conda_packages = {repr(self.conda_packages)},  "
                f"pip_packages = {repr(self.pip_packages)}"
                f")")

    def __str__(self):
        handle = io.StringIO()
        yaml.safe_dump(self._to_yml_dict(), handle)
        return "Environment:\n" + handle.getvalue()
