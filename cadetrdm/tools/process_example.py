import argparse
import os
import shutil
from abc import abstractmethod
from pathlib import Path
import subprocess

from cadetrdm import ProjectRepo, Options
from cadetrdm.wrapper import tracks_results


class ParallelizationBase:
    def __init__(self, n_cores=1):
        self.n_cores = n_cores

    @abstractmethod
    def run(self, func, args_list):
        """Run a function over a list of input args and return the output.

        Parameters
        ----------
        func : callable
            The function wrapping the shell command.
        args_list : list | iterable
            List of args to the func.

        Returns
        -------
        List of function returns
        """
        return


class SequentialBackend(ParallelizationBase):
    def run(self, func, args_list):
        results = []
        for args in args_list:
            results.append(func(*args))
        return results

#
class JoblibBackend(ParallelizationBase):
    def run(self, func, args_list):
        from joblib import Parallel, delayed
        Parallel(n_jobs=self.n_cores)(delayed(func)(*args) for args in args_list)


class PathosBackend(ParallelizationBase):
    def run(self, func, args_list):
        import pathos
        with pathos.pools.ProcessPool(ncpus=self.n_cores) as pool:
            # *zip(*args_list) because for multiple args, pathos expects (func, args1_list, args2_list)
            results = pool.map(func, *zip(*args_list))
        return results


def run_func_over_args_list(func, args_list, backend=None, n_cores=1):
    """Run a function over a list of input args and return the output.

    Parameters
    ----------
    func : callable
        The function wrapping the shell command.
    args_list : list | iterable
        List of tuple of args to the func.
    backend : ParallelizationBase, optional
        Backend for parallelization. Default is SequentialBackend
    n_cores : int, optional
        Number of cores to use for parallelization

    Returns
    -------
    List of function returns
    """
    if type(args_list[0]) not in (list, tuple):
        args_list = [(x,) for x in args_list]

    if backend is None and n_cores == 1:
        backend = SequentialBackend()
    else:
        backend = PathosBackend(n_cores=n_cores)

    return backend.run(func, args_list)


def run_command(command):
    """Run a shell command and return its output.

    Parameters
    ----------
    command : str
        The shell command to run_yml.

    Returns
    -------
    None
    """
    print(command)
    return subprocess.run(command, shell=True, check=True)


def remove_non_jupytext_files(file_list):
    """
    Filter out all python files that do not have a 'jupytext:' header section.

    :param file_list:
    :return:
    """
    if len(file_list) == 0:
        raise RuntimeError("No python files found in repository")
    filtered_list = []
    for file in file_list:
        with open(file, "r", encoding="utf8") as handle:
            lines = handle.readlines()
        if any("jupytext:" in line for line in lines):
            filtered_list.append(file)
    if len(file_list) == 0:
        raise RuntimeError("All python files found in repository are not tagged with jupytext.")
    return filtered_list


def create_output(root_path: Path, output_path: Path, n_cores=1):
    """Create solution files.

    Parameters
    ----------
    root_path : Path
        Root directory wherein all .py files are located
    output_path : Path
        Root directory where all compiled .ipynbs should be placed
    n_cores : int, optional
        Number of cpu cores to use for parallelization

    Returns
    -------
    None
    """
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    shutil.copytree(root_path, output_path)

    # Find all myst files recursively
    python_files = list(output_path.glob("**/*.py"))

    # Filter out checkpoints
    python_files = [
        file for file in python_files if (".ipynb_checkpoints" not in file.as_posix())
    ]

    # Filter out python files that are not marked for jupytext conversion
    python_files = remove_non_jupytext_files(python_files)

    # Make ipynbs
    ipynb_files = [file.with_suffix(".ipynb") for file in python_files]

    # Run jupytext for each myst file
    run_func_over_args_list(
        func=convert_python_to_ipynb,
        args_list=[
            (python_path.as_posix(), ipynb_path.as_posix())
            for python_path, ipynb_path in zip(python_files, ipynb_files)
        ],
        n_cores=n_cores,
    )


def convert_python_to_ipynb(myst_file_path, ipynb_file_path):
    """Run jupytext with --output ipynb flag on myst_file_path. Will skip README files.
    Will run_yml the jupyter notebooks.

    Parameters
    ----------
    myst_file_path : str
        path to myst file as posix.

    ipynb_file_path : str
        path to output ipynb file as posix.

    Returns
    -------
    None
    """
    if "README" in myst_file_path:
        return
    results = run_command(
        f'jupytext --output "{ipynb_file_path}" --execute "{myst_file_path}"'
    )
    return results


@tracks_results
def process_example(repo: ProjectRepo, options, **kwargs):
    """Run post-commit tasks based on command-line arguments.

    Returns
    -------
    None
    """
    parser = argparse.ArgumentParser(description="Perform post-commit tasks.")
    parser.add_argument("--n_cores", help="Number of cores to use.")

    args = parser.parse_args()

    # This isn't great, but for now (and with argparse) the best I could think of
    for kwarg_key, kwarg_value in kwargs.items():
        if kwarg_value is None:
            continue
        args.__setattr__(kwarg_key, kwarg_value)

    if args.n_cores is None:
        args.n_cores = 1

    create_output(
        root_path=repo.path / options.source_directory,
        output_path=repo.output_path / options.source_directory,
        n_cores=args.n_cores,
    )


"""Example usage:
    options = Options()
    options.commit_message = "Process example"
    options.debug = False
    options.push = True
    options.source_directory = "src"
    main(options)
"""
