import os
import shutil
from _stat import S_IWRITE
from pathlib import Path
from typing import Any, Callable


def add_linebreaks(input_list: list[str], initial_linebreak: bool = True) -> list[str]:
    """
    Add linebreaks between each entry in the input_list.

    Parameters
    ----------
    input_list : list[str]
        List of strings to add linebreaks to.
    initial_linebreak : bool, optional
        If True, add a newline before the first line.

    Returns
    -------
    list[str]
        Lines with trailing newlines.
    """
    lines = [line + "\n" for line in input_list]
    if initial_linebreak:
        lines = ["\n"] + lines
    return lines


def write_lines_to_file(
    path: str | Path,
    lines: list[str],
    open_type: str = "a",
) -> None:
    """
    Write lines to a file at path with added newlines between each line.

    Parameters
    ----------
    path : str | Path
        Path to file.
    lines : list[str]
        List of lines to be written to file.
    open_type : str, optional
        The way the file should be opened. I.e. "a" for append and "w" for fresh write.
    """
    add_initial_linebreak = False

    if os.path.exists(path) and open_type == "a":
        with open(path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()
        if len(existing_lines) > 0 and not existing_lines[-1].endswith("\n"):
            add_initial_linebreak = True

    with open(path, open_type, encoding="utf-8") as f:
        f.writelines(add_linebreaks(lines, initial_linebreak=add_initial_linebreak))


def is_tool(name: str) -> bool:
    """Check whether `name` is on PATH and marked as executable."""
    from shutil import which
    return which(name) is not None


def recursive_chmod(path: str | Path, setting: int) -> None:
    """
    Change the mode of a directory and all files and directories within it.

    Parameters
    ----------
    path : str | Path
        Root directory.
    setting : int
        Mode passed to os.chmod.
    """
    for dirpath, dirnames, filenames in os.walk(path):
        os.chmod(dirpath, setting)
        for filename in filenames:
            os.chmod(os.path.join(dirpath, filename), setting)


def delete_path(filename: str | Path) -> None:
    """
    Delete a file or directory, including read-only files on Windows.

    Parameters
    ----------
    filename : str | Path
        Path to the file or directory.
    """

    def remove_readonly(func: Callable[[str], Any], path: str, exc_info: tuple) -> None:
        # Clear the readonly bit and reattempt the removal
        # ERROR_ACCESS_DENIED = 5
        if func not in (os.unlink, os.rmdir) or exc_info[1].winerror != 5:
            raise exc_info[1]
        os.chmod(path, S_IWRITE)
        func(path)

    absolute_path = os.path.abspath(filename)
    if os.path.isdir(absolute_path):
        shutil.rmtree(absolute_path, onerror=remove_readonly)
    else:
        os.remove(absolute_path)


def wait_for_user(message: str) -> bool:
    """
    Ask the user a yes/no question on the command line.

    Parameters
    ----------
    message : str
        Question to show.

    Returns
    -------
    bool
        True if the user answered "y" or nothing, False otherwise.
    """
    proceed = input(message + " Y/n \n")
    if proceed.lower() == "y" or proceed == "":
        return True
    else:
        return False


def init_lfs(lfs_filetypes: list[str], path: str | Path | None = None) -> None:
    """
    Initialize lfs in the git repository at the path.

    Parameters
    ----------
    lfs_filetypes : list[str]
        List of file types to be handled by lfs.
        Format should be e.g. ["*.jpg", "*.png"] for jpg and png files.
    path : str | Path | None, optional
        Path to the repository. If None, the current working directory is used.
    """
    if path is not None:
        previous_path = os.getcwd()
        os.chdir(path)
    else:
        previous_path = "."

    os.system("git lfs install")
    lfs_filetypes_string = " ".join(lfs_filetypes)
    os.system(f"git lfs track {lfs_filetypes_string}")

    if path is not None:
        os.chdir(previous_path)


def test_for_lfs() -> None:
    """
    Raise an error if Git LFS is not installed.

    Raises
    ------
    RuntimeError
        If git-lfs is not on PATH.
    """
    if not is_tool("git-lfs"):
        raise RuntimeError(
            "Git LFS is not installed. Please install it via e.g. apt-get install git-lfs or the "
            "instructions found below \n"
            "https://docs.github.com/en/repositories/working-with-files"
            "/managing-large-files/installing-git-large-file-storage"
        )
