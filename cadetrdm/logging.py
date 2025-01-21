from pathlib import Path
import re

import semantic_version
from tabulate import tabulate
import yaml

class OutputLog:
    def __init__(self, filepath=None):
        # ToDo add classmethod for initialization from list of lists
        if not Path(filepath).exists():
            self._entry_list = [[], []]
            self.entries = []
            return

        self._filepath = filepath
        self._entry_list = self._read_file(filepath)
        self.entries = self._entries_from_entry_list(self._entry_list)

    def __iter__(self):
        self._index = 0
        return self

    def __next__(self):
        try:
            entry = self.entries[self._index]
            self._index += 1
            return entry
        except IndexError:
            raise StopIteration

    def _entries_from_entry_list(self, entry_list):
        header = self._convert_header(entry_list[0])
        if len(header) < 9:
            header.append("options_hash")
        entry_list = entry_list[1:]
        entry_dictionaries = []
        for entry in entry_list:
            if len(entry) < len(header):
                entry += [""] * (len(header) - len(entry))

            entry_dictionaries.append(
                {key: value for key, value in zip(header, entry)}
            )
        return [LogEntry(**entry, filepath=self._filepath) for entry in entry_dictionaries]

    def _read_file(self, filepath):
        with open(filepath) as handle:
            lines = handle.readlines()
        lines = [line.replace("\n", "").split("\t") for line in lines]
        return lines

    def _convert_header(self, header):
        return [entry.lower().replace(" ", "_") for entry in header]

    def __str__(self):
        return tabulate(self._entry_list[1:], headers=self._entry_list[0])


class LogEntry:
    def __init__(self, output_repo_commit_message, output_repo_branch, output_repo_commit_hash,
                 project_repo_commit_hash, project_repo_folder_name, project_repo_remotes, python_sys_args, tags,
                 options_hash, filepath, **kwargs):
        self.output_repo_commit_message = output_repo_commit_message
        self.output_repo_branch = output_repo_branch
        self.output_repo_commit_hash = output_repo_commit_hash
        self.project_repo_commit_hash = project_repo_commit_hash
        self.project_repo_folder_name = project_repo_folder_name
        self.project_repo_remotes = project_repo_remotes
        self.python_sys_args = python_sys_args
        self.tags = tags
        self.options_hash = options_hash
        self._filepath = filepath
        self._packages = None
        for key, value in kwargs:
            setattr(self, key, value)

    def __repr__(self):
        return f"OutputEntry('{self.output_repo_commit_message}', '{self.output_repo_branch}')"

    def _load_packages(self):
        environment_path = (
                Path(self._filepath).parent
                / "run_history"
                / self.output_repo_branch
                / "conda_environment.yml"
        )
        with open(environment_path) as handle:
            yml_string = "".join(handle.readlines())
            ansi_escape_pattern = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
            yml_string = re.sub(ansi_escape_pattern, "", yml_string)
            packages = yaml.safe_load(yml_string)

        conda_packages = packages["dependencies"]
        conda_packages = {line.split("=")[0]: line.split("=")[1] for line in conda_packages if isinstance(line, str)}
        self._packages = conda_packages

        if "pip" in packages["dependencies"][-1].keys():
            pip_packages = packages["dependencies"][-1]["pip"]
            pip_packages = {line.split("==")[0]: line.split("==")[1] for line in pip_packages}
            self._packages.update(pip_packages)

    def package_version(self, package):
        """
        Retrieves the version of the specified package.

        Args:
            package (str): The name of the package for which the version is to be retrieved.

        Returns:
            str: The version of the specified package.
        """
        if self._packages is None:
            self._load_packages()

        return self._packages[package]

    def check_package_version(self, package: str, version: str):
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
        if self._packages is None:
            self._load_packages()

        package_version = self.package_version(package)

        return semantic_version.match(version, package_version)


if __name__ == '__main__':
    output_log = OutputLog(filepath=r"C:\Users\ronal\PycharmProjects\CADET-RDM\tests\test_repo\results\log.tsv")
    print(output_log.entries)
    print(output_log.entries[1].package_version("cadet"))
    print(output_log.entries[1].check_package_version("cadet", ">4.4.0"))
    print(output_log.entries[1].check_package_version("cadet", "~4.4.0"))

    output_log = OutputLog(
        filepath=r"C:\Users\ronal\PycharmProjects\CADET-RDM\tests\test_repo\results\lognonexistant.tsv")
    print(output_log.entries)
