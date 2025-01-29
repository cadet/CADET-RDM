from pathlib import Path
from typing import Dict

from tabulate import tabulate

from cadetrdm.environment import Environment


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
        self._environment: Environment = None
        for key, value in kwargs:
            setattr(self, key, value)

    def __repr__(self):
        return f"OutputEntry('{self.output_repo_commit_message}', '{self.output_repo_branch}')"

    @property
    def environment(self):
        if self._environment is None:
            self._load_environment()

        return self._environment

    def _load_environment(self):
        environment_path = (
                Path(self._filepath).parent
                / "run_history"
                / self.output_repo_branch
                / "conda_environment.yml"
        )
        self._environment = Environment.from_yml(environment_path)

    def matches_options_hash(self, options_hash):
        return self.options_hash == options_hash

    def matches_study_hash(self, study_hash):
        return self.project_repo_commit_hash == study_hash

    def fulfils_environment(self, environment: Environment):
        """
        Checks if this environment fulfils the requirements in a given environment.

        :param environment:
            Instance of Environment class, with requirements as key: value pairs.
        :return:
        """
        if self._environment is None:
            self._load_environment()

        return self._environment.fulfils_environment(environment)

    def package_version(self, package):
        """
        Retrieves the version of the specified package.

        Args:
            package (str): The name of the package for which the version is to be retrieved.

        Returns:
            str: The version of the specified package.
        """
        if self._environment is None:
            self._load_environment()

        return self._environment[package]

    def fulfils(self, package: str, version: str):
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
        if self._environment is None:
            self._load_environment()

        return self._environment.fulfils(package, version)


class OutputLog:
    def __init__(self, filepath=None):
        if not Path(filepath).exists():
            self._entry_list = [[], []]
            self.entries = []
            return

        self._filepath = filepath
        self._entry_list = self._read_file(filepath)
        self.entries: Dict[str, LogEntry] = self._entries_from_entry_list(self._entry_list)

    def _entries_from_entry_list(self, entry_list) -> Dict[str, LogEntry]:
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
        return {entry["output_repo_branch"]: LogEntry(**entry, filepath=self._filepath) for entry in entry_dictionaries}

    def _read_file(self, filepath):
        with open(filepath) as handle:
            lines = handle.readlines()
        lines = [line.replace("\n", "").split("\t") for line in lines]
        return lines

    def _convert_header(self, header):
        return [entry.lower().replace(" ", "_") for entry in header]

    def __str__(self):
        return tabulate(self._entry_list[1:], headers=self._entry_list[0])
