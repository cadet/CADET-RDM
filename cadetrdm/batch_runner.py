import importlib
from pathlib import Path
import sys

from cadetrdm import clone, Options, ProjectRepo


class Study(ProjectRepo):
    def __init__(self, path, url, branch="main", *args, **kwargs):
        self.name = Path(path).parts[-1]
        self.url = url

        try:
            if not path.exists():
                clone(self.url, path)
                if branch != "main":
                    ProjectRepo(path).checkout(branch)
        except Exception as e:
            print(f"Error processing study {self.name}: {e}")
            return

        super().__init__(path, *args, **kwargs)


class Case:
    def __init__(self, study: Study, options: Options, name: str = None):
        if name is None:
            name = options.hash

        self.name = name
        self.study = study
        self.options = options

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
        output_log = self.study.output_log
        for log_entry in output_log:
            if (self.study.current_commit_hash == log_entry.project_repo_commit_hash
                    and self.options.hash == log_entry.options_hash):
                return True

        return False

    def run_study(self, force=False):
        """Run specified study commands in the given repository."""
        if self.is_running and not force:
            print(f"{self.study.name} is currently running. Skipping...")
            return

        print(f"Running {self.name} in {self.study.path} with: {self.options}")
        if not self.options.debug:
            self.study.update()
        else:
            print("WARNING: Not updating the repositories while in debug mode.")

        if self.has_results_for_this_run and not force:
            print(f"{self.study.path} has already been computed with these options. Skipping...")
            return

        try:
            sys.path.append(str(self.study.path))
            module = importlib.import_module(self.study.name)

            self.status = 'running'

            module.main(self.options, str(self.study.path))

            print("Command execution successful.")
            self.status = 'finished'

            sys.path.remove(str(self.study.path))

        except (KeyboardInterrupt, Exception) as e:
            print(f"Command execution failed: {e}")
            self.status = 'failed'
            return
