import traceback
from pathlib import Path
import subprocess
from typing import Dict

from .study import Study
from .options import Options
from cadetrdm.environment import Environment
from ..logging import LogEntry


class Case:
    def __init__(self, study: Study, options: Options, environment: Environment = None, name: str = None):
        if name is None:
            name = options.get_hash()

        self.name = name
        self.study = study
        self.options = options
        self.environment = environment
        self._options_hash = options.get_hash()
        self._results_branch = None
        self._current_environment = None

    @property
    def status_file(self):
        return Path(self.study.path).parent / (Path(self.study.path).name + ".status")

    @property
    def status(self):
        status, _ = self._read_status()
        return status

    @status.setter
    def status(self, status):
        """Update the status file with the current execution status."""

        with open(self.status_file, "w") as f:
            f.write(f"{status}@{self.study.current_commit_hash}")

    @property
    def status_hash(self):
        _, status_hash = self._read_status()
        return status_hash

    def _read_status(self):
        """Check the status of the study and decide whether to proceed.

        Args:
            repo_path (Path): The path to the repository containing the status file.

        Returns:
            tuple: A tuple containing the status string and the current hash,
            or None, None if the status cannot be determined.
        """

        if not self.status_file.exists():
            return None, None

        with open(self.status_file) as f:
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
    def is_running(self, ):
        if self.status == 'running':
            return True

        return False

    @property
    def has_results_for_this_run(self):
        self._results_branch = self._get_results_branch()
        if self._results_branch is None:
            return False
        else:
            return True

    def _get_results_branch(self):
        """
        Search the output log for an entry (i.e. a results branch) with matching study commit hash and options hash.
        If environment is given, the environment is also enforced.

        :return:
        str: name of the results branch or None.
        """
        output_log: Dict[str, LogEntry] = self.study.output_log.entries
        options_hash = self.options.get_hash()
        study_hash = self.study.current_commit_hash

        found_results_with_incorrect_study_hash = False
        found_results_with_incorrect_options = False
        found_results_with_incorrect_environment = False

        semi_correct_hits = []
        for output_branch, log_entry in output_log.items():
            matches_study_hash = log_entry.matches_study_hash(study_hash)
            matches_options_hash = log_entry.matches_options_hash(options_hash)
            matches_environment = log_entry.fulfils_environment(self.environment)

            if matches_study_hash and matches_options_hash and matches_environment:
                return log_entry.output_repo_branch

            elif matches_study_hash and not matches_options_hash and matches_environment:
                found_results_with_incorrect_options = True
                semi_correct_hits.append(
                    f"Found matching study commit hash {study_hash[:7]}, but incorrect options hash "
                    f"(needs: {options_hash[:7]}, has: {log_entry.options_hash[:7]})"
                )

            elif not matches_study_hash and matches_options_hash and matches_environment:
                found_results_with_incorrect_study_hash = True
                semi_correct_hits.append(
                    f"Found matching options hash  {options_hash[:7]}, but incorrect study commit hash "
                    f"(needs: {study_hash[:7]}, has: {log_entry.project_repo_commit_hash[:7]})"
                )
            elif matches_study_hash and matches_options_hash and not matches_environment:
                found_results_with_incorrect_environment = True
                semi_correct_hits.append(
                    f"Found matching options hash  {options_hash[:7]}, matching study commit hash "
                    f"{study_hash[:7]}, but wrong environment specification."
                )

        if found_results_with_incorrect_study_hash:
            [print(line) for line in semi_correct_hits]
            print(
                "No matching results were found for this study version, but results with these options were found for "
                "other study versions. Did you recently update the study?"
            )
        elif found_results_with_incorrect_options:
            [print(line) for line in semi_correct_hits]
            print(
                "No matching results were found for these options, but results with other options were found for "
                "this study versions. Did you recently change the options?"
            )
        elif found_results_with_incorrect_environment:
            [print(line) for line in semi_correct_hits]
            print(
                "No matching results were found for this environment, but results with other environments were "
                "found for this study versions."
            )

        else:
            print("No matching results were found for these options and study version.")
        return None

    def run_study(self, force=False) -> bool:
        """
        Run specified study commands in the given repository.

        :returns
            boolean indicating if the results for this case are available, either pre-computed or computed now.

        """
        if not force and self.is_running:
            print(f"{self.study.name} is currently running. Skipping...")
            return False

        print(f"Running {self.name} in {self.study.path} with: {self.options}")
        if not self.options.debug:
            self.study.update()
        else:
            print("WARNING: Not updating the repositories while in debug mode.")

        if not force and self.has_results_for_this_run:
            print(f"{self.study.path} has already been computed with these options. Skipping...")
            return True

        if not self.can_run_study:
            print(f"Current environment does not match required environment. Skipping...")
            self.status = 'failed'
            return False

        try:
            self.status = 'running'

            self.study.module.main(self.options, str(self.study.path))

            print("Command execution successful.")
            self.status = 'finished'
            return True

        except (KeyboardInterrupt, Exception) as e:
            traceback.print_exc()
            self.status = 'failed'
            return False

    @property
    def can_run_study(self) -> bool:
        return self.environment is None or self._check_execution_environment()

    def _check_execution_environment(self):
        if self._current_environment is None:
            existing_environment = subprocess.check_output(f"conda env export", shell=True).decode()
            self._current_environment = Environment.from_yml_string(existing_environment)

        return self._current_environment.fulfils_environment(self.environment)

    @property
    def _results_path(self):
        if self._results_branch is None:
            return None
        else:
            return self.study.path / (self.study._output_folder + "_cached") / self._results_branch

    def load(self, ):
        if self._results_branch is None or self.options.get_hash() != self._options_hash:
            self._results_branch = self._get_results_branch()
            self._options_hash = self.options.get_hash()

        if self._results_branch is None:
            print(f"No results available for Case({self.study.path, self.options.get_hash()[:7]})")
            return None

        if self._results_path.exists():
            return

        self.study.copy_data_to_cache(self._results_branch)

    @property
    def results_path(self):
        self.load()

        return self._results_path
