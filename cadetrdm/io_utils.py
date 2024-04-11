import os
import shutil
from _stat import S_IWRITE
from pathlib import Path


def add_linebreaks(input_list, initial_linebreak=True):
    """
    Add linebreaks between each entry in the input_list

    :param input_list:
    List of strings to add linebreaks to.

    :param initial_linebreak:
    Bool, if true: add a newline before the first line.
    """
    lines = [line + "\n" for line in input_list]
    if initial_linebreak:
        lines = ["\n"] + lines
    return lines


def write_lines_to_file(path, lines, open_type="a"):
    """
    Convenience function. Write lines to a file at path with added newlines between each line.
    :param path:
        Path to file.
    :param lines:
        List of lines to be written to file.
    :param open_type:
        The way the file should be opened. I.e. "a" for append and "w" for fresh write.
    """

    add_initial_linebreak = False

    if os.path.exists(path) and open_type == "a":
        with open(path, "r") as f:
            existing_lines = f.readlines()
        if len(existing_lines) > 0 and not existing_lines[-1].endswith("\n"):
            add_initial_linebreak = True

    with open(path, open_type) as f:
        f.writelines(add_linebreaks(lines, initial_linebreak=add_initial_linebreak))


def is_tool(name):
    """Check whether `name` is on PATH and marked as executable."""

    from shutil import which
    return which(name) is not None


def recursive_chmod(path, setting):
    for dirpath, dirnames, filenames in os.walk(path):
        os.chmod(dirpath, setting)
        for filename in filenames:
            os.chmod(os.path.join(dirpath, filename), setting)


def delete_path(filename):
    def remove_readonly(func, path, exc_info):
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


def wait_for_user(message):
    proceed = input(message + " Y/n \n")
    if proceed.lower() == "y" or proceed == "":
        return True
    else:
        return False


def init_lfs(lfs_filetypes: list, path: str | Path = None):
    """
    Initialize lfs in the git repository at the path.
    If path is None, the current working directory is used.
    :param lfs_filetypes:
        List of file types to be handled by lfs.
        Format should be e.g. ["*.jpg", "*.png"] for jpg and png files.
    """
    if path is not None:
        previous_path = os.getcwd()
        os.chdir(path)
    else:
        previous_path = "."

    os.system(f"git lfs install")
    lfs_filetypes_string = " ".join(lfs_filetypes)
    os.system(f"git lfs track {lfs_filetypes_string}")

    if path is not None:
        os.chdir(previous_path)


def test_for_lfs():
    if not is_tool("git-lfs"):
        raise RuntimeError("Git LFS is not installed. Please install it via e.g. apt-get install git-lfs or the "
                           "instructions found below \n"
                           "https://docs.github.com/en/repositories/working-with-files"
                           "/managing-large-files/installing-git-large-file-storage")
