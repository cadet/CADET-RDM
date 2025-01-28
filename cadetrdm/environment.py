import re

from addict import Dict
import yaml
import semantic_version


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

        # Remove special formatting characters from the string
        ansi_escape_pattern = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
        yml_string = re.sub(ansi_escape_pattern, "", yml_string)

        instance = cls.from_yml_string(yml_string)
        return instance

    @classmethod
    def from_yml_string(cls, yml_string):
        """
        Creates an Environment object from a YAML string.

        :param yml_string:
        :return:
        """
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
            check_package_version("conda", "~0.1.1") -> true if approximately equal (excluding pre-release suffixes)
            check_package_version("conda", "0.1.1") -> true if exactly equal

        Uses semantic versioning to compare the versions.
        """

        package_version = self[package]

        return semantic_version.match(version, package_version)
