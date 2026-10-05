from __future__ import annotations

import os
import traceback
import warnings
from pathlib import Path
import subprocess
from typing import Any

from cadetrdm.batch_running import Study
from cadetrdm.repositories import OutputRepo, ProjectRepo
from cadetrdm import Options
from cadetrdm.environment import Environment


class Case:
    """A project repository run with a specific set of options and environment."""

    def __init__(
        self,
        project_repo: ProjectRepo | os.PathLike = "./",
        options: Options | None = None,
        environment: Environment | None = None,
        name: str | None = None,
        study: Study | None = None,
        run_method: str = "main"
     ) -> None:
        if study is not None:
            warnings.warn(
                "Initializing Case() with the study= kwarg is deprecated "
                "and will be removed in the future. Please use project_repo=",
                FutureWarning
            )
            project_repo = study

        if name is None:
            name = project_repo.name + "_" + options.get_hash()

        self.name = name

        if not isinstance(project_repo, ProjectRepo):
            project_repo = ProjectRepo(project_repo)
        self.project_repo = project_repo
        self.options = options

        self._current_environment = None
        self.environment = environment

        self.run_method = run_method

        self._results_branch = None
        self._results_path = None

    def __str__(self) -> str:
        """Return the name of the case."""
        return self.name

    @property
    def options_hash(self) -> str:
        """Hash of the case options."""
        return self.options.get_hash()

    @property
    def output_repo(self) -> OutputRepo:
        """Output repository of the project repository."""
        return self.project_repo.output_repo

    @property
    def status_file(self) -> Path:
        """File next to the project repository that stores the execution status."""
        return Path(self.project_repo.path).parent / (Path(self.project_repo.path).name + ".status")

    @property
    def status(self) -> str | None:
        """Execution status of the case."""
        status, _ = self._read_status()
        return status

    @status.setter
    def status(self, status: str) -> None:
        with open(self.status_file, "w", encoding="utf-8") as f:
            f.write(f"{status}@{self.project_repo.current_commit_hash}")

    @property
    def status_hash(self) -> str | None:
        """Project repository commit hash the status was written for."""
        _, status_hash = self._read_status()
        return status_hash

    def _read_status(self) -> tuple[str | None, str | None]:
        """
        Read the execution status and commit hash from the status file.

        Returns
        -------
        tuple[str | None, str | None]
            The status string and the commit hash,
            or None, None if the status cannot be determined.
        """
        if not self.status_file.exists():
            return None, None

        with open(self.status_file, encoding="utf-8") as f:
            status = f.read().strip()
            try:
                status, current_hash = status.split("@")
            except ValueError as e:
                if status == '':
                    return None, None
                else:
                    raise e

            return status, current_hash

    @property
    def is_running(self) -> bool:
        """True if the status file marks the case as running."""
        if self.status == 'running':
            return True

        return False

    def run_study(
        self,
        force: bool = False,
        **load_kwargs: Any,
    ) -> Path | None:
        """
        Run specified study commands in the given repository.

        Parameters
        ----------
        force : bool, optional
            If True, run even if the case is marked as running or results already exist.
        **load_kwargs : Any
            Keyword arguments passed to load() when looking for existing results.

        Returns
        -------
        Path | None
            Path to results for this case if available (either pre-computed or newly
            computed), else None.
        """
        if not force and self.is_running:
            print(f"{self.project_repo.name} is currently running. Skipping...")
            return False

        print(f"Running {self.name} in {self.project_repo.path} with: {self.options}")
        if not self.options.debug:
            self.project_repo.update()
            self.output_repo.update_main()
        else:
            print("WARNING: Not updating the repositories while in debug mode.")

        results_path = self.load(**load_kwargs)

        if results_path and not force:
            print(
                f"{self.project_repo.path} has already been computed with these options. "
                "Skipping..."
            )
            return results_path

        if self.can_run_study is False:
            print("Current environment does not match required environment. Skipping...")
            self.status = 'failed'
            return

        try:
            self.status = 'running'

            module = self.project_repo.module
            run_method = getattr(module, self.run_method)
            run_method(self.options, str(self.project_repo.path))

            print("Command execution successful.")
            self.status = 'finished'
            results_path = self.load()
            return results_path

        except (KeyboardInterrupt, Exception):
            traceback.print_exc()
            self.status = 'failed'
            return

    @property
    def can_run_study(self) -> bool:
        """True if the current environment fulfils the required environment."""
        return (
            self.environment is None
            or
            self.current_environment.fulfils_environment(self.environment)
        )

    @property
    def current_environment(self) -> Environment:
        """Environment exported from the active conda environment."""
        if self._current_environment is None:
            existing_environment = subprocess.check_output(
                "conda env export", shell=True
            ).decode()
            self._current_environment = Environment.from_yml_string(
                existing_environment
            )

        return self._current_environment

    @property
    def has_results_for_this_run(self) -> bool:
        """True if results exist for the current options and commit."""
        if self.results_branch is None:
            return False
        else:
            return True

    @property
    def results_branch(self) -> str | None:
        """Output branch with results for the current options and commit."""
        return self._get_results_branch()

    def _get_results_branch(
        self,
        allow_commit_hash_mismatch: bool = False,
        allow_options_hash_mismatch: bool = False,
        allow_environment_mismatch: bool = False,
    ) -> str | None:
        """
        Return the output branch matching the current study and options.

        Parameters
        ----------
        allow_commit_hash_mismatch : bool, optional
            If True, allow mismatched study commit hash.
        allow_options_hash_mismatch : bool, optional
            If True, allow mismatched options hash.
        allow_environment_mismatch : bool, optional
            If True, allow mismatched environment.

        Returns
        -------
        str | None
            Name of the results branch, or None if no match found.
        """
        options_hash = self.options_hash
        commit_hash = self.project_repo.current_commit_hash
        log_entries = self.output_repo.output_log.entries

        for output_repo_branch, entry in reversed(log_entries.items()):
            environment_ok = entry.fulfils_environment(self.environment)

            # Exact match (all properties match)
            if (
                entry.options_hash == options_hash
                and entry.project_repo_commit_hash == commit_hash
                and environment_ok
            ):
                return output_repo_branch

            # Check environment
            if not allow_environment_mismatch and not environment_ok:
                continue

            # Check study hash
            if entry.project_repo_commit_hash != commit_hash and not allow_commit_hash_mismatch:
                continue

            # Check options hash
            if entry.options_hash != options_hash and not allow_options_hash_mismatch:
                continue

            # Semi-correct match (at least one mismatch, but allowed)
            msg_parts = []
            if entry.options_hash != options_hash:
                msg_parts.append(
                    "mismatched options hash "
                    f"(needs: {options_hash[:7]}, "
                    f"has: {entry.options_hash[:7]})"
                )
            if entry.project_repo_commit_hash != commit_hash:
                msg_parts.append(
                    "mismatched project repo hash "
                    f"(needs: {commit_hash[:7]}, "
                    f"has: {entry.project_repo_commit_hash[:7]})"
                )
            if not entry.fulfils_environment(self.environment):
                msg_parts.append("mismatched environment")

            if msg_parts:
                msg = "Found matching entry with: " + ", ".join(msg_parts)
                print(f"{msg}. Using results from branch: {output_repo_branch}")
                return output_repo_branch

        print("No matching results found.")

    @property
    def results_path(self) -> Path | None:
        """Path to the cached results of this case."""
        return self.load()

    def load(
        self,
        allow_commit_hash_mismatch: bool = False,
        allow_options_hash_mismatch: bool = False,
        allow_environment_mismatch: bool = False,
    ) -> Path | None:
        """
        Load results for the current case.

        Parameters
        ----------
        allow_commit_hash_mismatch : bool, optional
            If True, allow loading results with mismatched study commit hash.
        allow_options_hash_mismatch : bool, optional
            If True, allow loading results with mismatched options hash.
        allow_environment_mismatch : bool, optional
            If True, allow loading results with mismatched environment.

        Returns
        -------
        Path | None
            Path to results, or None if no results are available.
        """
        results_branch = self._get_results_branch(
            allow_commit_hash_mismatch=allow_commit_hash_mismatch,
            allow_options_hash_mismatch=allow_options_hash_mismatch,
            allow_environment_mismatch=allow_environment_mismatch,
        )

        # Early exit if no results are available
        if results_branch is None:
            print(
                f"No results available for Case("
                f"project_repo={self.project_repo.path}, "
                f"options_hash={self.options_hash[:7]}"
                f")"
            )
            return

        # Load results if the path exists, otherwise fetch them
        results_path = self.project_repo.copy_data_to_cache(results_branch)
        if not results_path.exists():
            print("Failed to fetch results.")
            return

        return results_path
