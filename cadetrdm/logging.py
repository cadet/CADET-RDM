import csv
from pathlib import Path
from typing import Dict, List

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
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"OutputEntry('{self.output_repo_commit_message}', '{self.output_repo_branch}')"

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}

    @property
    def environment(self):
        if self._filepath is None:
            raise ValueError("OutputLog was initialized without a filepath, can not load Environment data.")
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

        return self._environment.packages[package]

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
        self._filepath = filepath

        if filepath is None or not Path(filepath).exists():
            self._entry_list = [[], []]
            self.entries = {}
            return

        self._entry_list = self._read_file(filepath)
        self.entries: Dict[str, LogEntry] = self._entries_from_entry_list(self._entry_list)

    @property
    def n_entries(self) -> int:
        """int: Number of results stored in the repository."""
        return len(self.entries)

    @classmethod
    def from_list(cls, entry_list: List[List[str]]):
        instance = cls()
        instance._entry_list = entry_list
        instance.entries: Dict[str, LogEntry] = instance._entries_from_entry_list(instance._entry_list)
        return instance

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

    def __repr__(self):
        return f"OutputLog.from_list({self._entry_list})"

    @property
    def header(self):
        collection_of_keys = None
        for entry in self.entries.values():
            if collection_of_keys is None:
                collection_of_keys = entry.to_dict()
            collection_of_keys.update(entry.to_dict())

        return collection_of_keys.keys()

    def write(self):
        if self._filepath is None:
            raise ValueError("No filepath set for output log. Can not write to filepath")

        with open(self._filepath, "w", newline="") as tsv_file_handle:
            writer = csv.DictWriter(tsv_file_handle, fieldnames=self.header, delimiter="\t")
            writer.writeheader()
            for entry in self.entries.values():
                writer.writerow(entry.to_dict())
