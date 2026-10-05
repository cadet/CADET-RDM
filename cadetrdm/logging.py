import csv
import os
from pathlib import Path
from typing import Any, Iterable, Self

from tabulate import tabulate

from cadetrdm.environment import Environment


class LogEntry:
    """A single row of the output repository log."""

    def __init__(
        self,
        output_repo_commit_message: str,
        output_repo_branch: str,
        output_repo_commit_hash: str,
        project_repo_branch: str,
        project_repo_commit_hash: str,
        project_repo_directory_name: str,
        project_repo_remotes: str,
        python_sys_args: str,
        tags: str,
        options_hash: str,
        filepath: os.PathLike,
        **kwargs: str,
    ) -> None:
        self.output_repo_commit_message = output_repo_commit_message
        self.output_repo_branch = output_repo_branch
        self.output_repo_commit_hash = output_repo_commit_hash
        self.project_repo_branch = project_repo_branch
        self.project_repo_commit_hash = project_repo_commit_hash
        self.project_repo_directory_name = project_repo_directory_name
        self.project_repo_remotes = project_repo_remotes
        self.python_sys_args = python_sys_args
        self.tags = tags
        self.options_hash = options_hash
        self._filepath = filepath
        self._environment: Environment = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        """Return the commit message and branch of the entry."""
        return f"OutputEntry('{self.output_repo_commit_message}', '{self.output_repo_branch}')"

    def to_dict(self) -> dict[str, Any]:
        """
        Return the public attributes of the entry.

        Returns
        -------
        dict[str, Any]
            Mapping of log column names to values.
        """
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}

    @property
    def environment(self) -> Environment:
        """Environment recorded for the run of this entry."""
        if self._filepath is None:
            raise ValueError(
                "OutputLog was initialized without a filepath, can not load Environment data."
            )
        if self._environment is None:
            self._load_environment()

        return self._environment

    def _load_environment(self) -> None:
        environment_path = (
            Path(self._filepath).parent
            / "run_history"
            / self.output_repo_branch
            / "conda_environment.yml"
        )
        self._environment = Environment.from_yml(environment_path)

    def matches_options_hash(self, options_hash: str) -> bool:
        """
        Check whether the entry was run with the given options hash.

        Parameters
        ----------
        options_hash : str
            Options hash to compare against.

        Returns
        -------
        bool
            True if the hashes match.
        """
        return self.options_hash == options_hash

    def matches_study_hash(self, study_hash: str) -> bool:
        """
        Check whether the entry was run at the given project repository commit.

        Parameters
        ----------
        study_hash : str
            Commit hash of the project repository.

        Returns
        -------
        bool
            True if the hashes match.
        """
        return self.project_repo_commit_hash == study_hash

    def fulfils_environment(self, environment: Environment | None) -> bool:
        """
        Check if the recorded environment fulfils the requirements in a given environment.

        Parameters
        ----------
        environment : Environment | None
            Environment with requirements as key: value pairs.
            If None, the requirements are always fulfilled.

        Returns
        -------
        bool
            True if all requirements are fulfilled.
        """
        # Environment matching is opt-in. Without requirements to check against, the
        # recorded environment is not read at all, so loading results does not depend
        # on the run_history files being present in the working tree.
        if environment is None:
            return True

        if self._environment is None:
            self._load_environment()

        return self._environment.fulfils_environment(environment)

    def package_version(self, package: str) -> str:
        """
        Retrieve the version of the specified package.

        Parameters
        ----------
        package : str
            The name of the package for which the version is to be retrieved.

        Returns
        -------
        str
            The version of the specified package.
        """
        if self._environment is None:
            self._load_environment()

        return self._environment.packages[package]

    def fulfils(self, package: str, version: str) -> bool:
        """
        Check if the recorded version of a package matches the specified version.

        Uses semantic versioning to compare the versions.

        Parameters
        ----------
        package : str
            The name of the package to check.
        version : str
            The version or specification string to match against.

        Returns
        -------
        bool
            True if the recorded package version matches the specified version,
            False otherwise.

        Examples
        --------
        >>> entry.fulfils("conda", ">=0.1.1")  # larger or equal
        >>> entry.fulfils("conda", "~0.1.1")  # excluding pre-release suffixes
        >>> entry.fulfils("conda", "0.1.1")  # exactly equal
        """
        if self._environment is None:
            self._load_environment()

        return self._environment.fulfils(package, version)


class OutputLog:
    """Contents of the log.tsv file of an output repository."""

    def __init__(self, filepath: os.PathLike | None = None) -> None:
        self._filepath = filepath

        if filepath is None or not Path(filepath).exists():
            self._entry_list = [[], []]
            self.entries = {}
            return

        self._entry_list = self._read_file(filepath)
        self.entries: dict[str, LogEntry] = self._entries_from_entry_list(self._entry_list)

    @property
    def n_entries(self) -> int:
        """int: Number of results stored in the repository."""
        return len(self.entries)

    @classmethod
    def from_string(cls, content: str, filepath: os.PathLike | None = None) -> Self:
        """
        Create an OutputLog from the raw contents of a log.tsv file.

        Used to read the log out of a git ref without checking that ref out. The
        filepath is not read from, but is retained so that LogEntry can resolve the
        run_history files next to it.

        Parameters
        ----------
        content : str
            Raw tab-separated contents of a log.tsv file.
        filepath : os.PathLike | None, optional
            Path the contents belong to.

        Returns
        -------
        OutputLog
            Log with one entry per row.
        """
        instance = cls()
        instance._filepath = filepath

        lines = cls._split_content(content)
        if not lines:
            return instance

        instance._entry_list = lines
        instance.entries = instance._entries_from_entry_list(instance._entry_list)
        return instance

    @classmethod
    def from_list(cls, entry_list: list[list[str]]) -> Self:
        """
        Create an OutputLog from a header row followed by entry rows.

        Parameters
        ----------
        entry_list : list[list[str]]
            Header row followed by one row per entry.

        Returns
        -------
        OutputLog
            Log with one entry per row.
        """
        instance = cls()
        instance._entry_list = entry_list
        instance.entries = instance._entries_from_entry_list(instance._entry_list)
        return instance

    def _entries_from_entry_list(self, entry_list: list[list[str]]) -> dict[str, LogEntry]:
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
        return {
            entry["output_repo_branch"]: LogEntry(**entry, filepath=self._filepath)
            for entry in entry_dictionaries
        }

    def _read_file(self, filepath: os.PathLike) -> list[list[str]]:
        with open(filepath, encoding="utf-8", newline="") as handle:
            return self._split_content(handle.read())

    @staticmethod
    def _split_content(content: str) -> list[list[str]]:
        """
        Split log.tsv contents into rows of tab-separated fields.

        A row ends at a line feed, optionally preceded by a carriage return.
        Empty lines are skipped.
        """
        return [line.rstrip("\r").split("\t") for line in content.split("\n") if line]

    def _convert_header(self, header: list[str]) -> list[str]:
        return [entry.lower().replace(" ", "_") for entry in header]

    def __str__(self) -> str:
        """Return the log as a table."""
        return tabulate(self._entry_list[1:], headers=self._entry_list[0])

    def __repr__(self) -> str:
        """Return the log as a from_list() call."""
        return f"OutputLog.from_list({self._entry_list})"

    @property
    def header(self) -> Iterable[str]:
        """Union of the column names of all entries."""
        collection_of_keys = None
        for entry in self.entries.values():
            if collection_of_keys is None:
                collection_of_keys = entry.to_dict()
            collection_of_keys.update(entry.to_dict())

        return collection_of_keys.keys()

    @staticmethod
    def _sanitize(value: Any) -> str:
        """
        Make a value safe to write as one tab-separated field.

        Tabs and line breaks are replaced by spaces, because a log entry must
        stay on a single line: log.tsv is tracked with `merge=union`, and the
        reader splits on tabs rather than parsing csv.
        """
        if value is None:
            return ""
        text = str(value)
        for char in ("\t", "\r", "\n"):
            text = text.replace(char, " ")
        return text

    def write(self) -> None:
        """
        Write the log to its filepath.

        Raises
        ------
        ValueError
            If the log has no filepath.
        """
        if self._filepath is None:
            raise ValueError("No filepath set for output log. Can not write to filepath")

        # Quoting is disabled because the reader does not unquote. Were a value
        # containing a quote written out quoted, the quotes would be read back
        # as part of the value and escaped again on the next write, doubling
        # the field in size with every run.
        with open(self._filepath, "w", newline="", encoding="utf-8") as tsv_file_handle:
            writer = csv.DictWriter(
                tsv_file_handle,
                fieldnames=self.header,
                delimiter="\t",
                quoting=csv.QUOTE_NONE,
                quotechar=None,
                escapechar=None,
            )
            writer.writeheader()
            for entry in self.entries.values():
                writer.writerow(
                    {key: self._sanitize(value) for key, value in entry.to_dict().items()}
                )
