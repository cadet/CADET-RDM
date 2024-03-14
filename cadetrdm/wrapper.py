from functools import wraps
from pathlib import Path
from copy import deepcopy

from cadetrdm.repositories import ProjectRepo
from cadetrdm.configuration_options import Options


def tracks_results(func):
    """Tracks results using CADET-RDM."""

    @wraps(func)
    def wrapper(options, repo_path='.'):
        if type(options) is str and Path(options).exists():
            options = Options.load_json_file(options)
        elif type(options) is str:
            options = Options.load_json_str(options)
        if type(options) is dict:
            options = Options(options)

        for key in ["commit_message", "debug"]:
            if key not in options or options[key] is None:
                raise ValueError(f"Key {key} not found in options. Please supply options.{key}")

        if options.get_hash() != Options.load_json_str(options.dump_json_str()).get_hash():
            raise ValueError("Options are not serializable. Please only use python natives and numpy ndarrays.")

        project_repo = ProjectRepo(repo_path)

        project_repo.options_hash = options.get_hash()

        with project_repo.track_results(
                options.commit_message,
                debug=options.debug,
                force=True
        ):
            options.dump_json_file(project_repo.output_path / "options.json")
            results = func(project_repo, options)

        if not options.debug and "push" in options and options["push"]:
            project_repo.push()

        return results

    return wrapper
