from functools import wraps
from pathlib import Path
from typing import Any, Callable

from cadetrdm.repositories import ProjectRepo
from cadetrdm import Options


def tracks_results(
    func: Callable[[ProjectRepo, Options], Any],
) -> Callable[..., tuple[str, Any]]:
    """
    Track the results of a function using CADET-RDM.

    The wrapped function receives the project repository and the options as arguments.
    The wrapper returns the output branch name together with the function results.

    Parameters
    ----------
    func : Callable[[ProjectRepo, Options], Any]
        Function that computes and writes results to the output directory.

    Returns
    -------
    Callable[..., tuple[str, Any]]
        Wrapper taking options and a repository path.
    """

    @wraps(func)
    def wrapper(
        options: Options | dict | str,
        repo_path: str | Path = '.',
    ) -> tuple[str, Any]:
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
            raise ValueError(
                "Options are not serializable. "
                "Please only use python natives and numpy ndarrays."
            )

        project_repo = ProjectRepo(repo_path)

        with project_repo.track_results(
                options.commit_message,
                debug=options.debug,
                force=True,
                options=options,
        ) as new_branch_name:
            options.dump_json_file(project_repo.output_path / "options.json")
            results = func(project_repo, options)

        if not options.debug and "push" in options and options["push"]:
            project_repo.push()

        return new_branch_name, results

    return wrapper
