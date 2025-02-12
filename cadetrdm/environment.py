import io
import re
from typing import Self, List
from typing import Dict as DictType
import subprocess

import yaml
from semantic_version import Version, SimpleSpec


class Environment(Dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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

        conda_packages = packages["dependencies"]
        conda_packages = {line.split("=")[0]: line.split("=")[1] for line in conda_packages if isinstance(line, str)}
        instance.update(conda_packages)

        if "pip" in packages["dependencies"][-1].keys():
            pip_packages = packages["dependencies"][-1]["pip"]
            pip_packages = {line.split("==")[0]: line.split("==")[1] for line in pip_packages}
            instance.update(pip_packages)

        return instance

    def package_version(self, package):
        return self[package]

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
        try:
            spec = SimpleSpec(version)
        except ValueError as e:
            spec = SimpleSpec(str(Version.coerce(version)))
            print(f"Warning: {e} when processing {package}={version}. Using {str(Version.coerce(version))} instead.")

        # Use .coerce instead of .parse to ensure non-standard version strings are converted.
        # Rules are:
        #   - If no minor or patch component, and partial is False, replace them with zeroes
        #   - Any character outside of a-zA-Z0-9.+- is replaced with a -
        #   - If more than 3 dot-separated numerical components,
        #       everything from the fourth component belongs to the build part
        #   - Any extra + in the build part will be replaced with dots
        installed_version = Version.coerce(self.package_version(package))

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

        for package, version in environment.items():
            if not self.fulfils(package, version):
                mismatches.append((package, version, self.package_version(package)))

        if mismatches:
            for package, version, existing_version in mismatches:
                print(f"Package {package}: {existing_version} does not fulfil requirements: {version}")
            return False

        return True
