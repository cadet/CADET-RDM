import os
import shutil
from _stat import S_IWRITE


def add_linebreaks(input_list):
    """
    Add linebreaks between each entry in the input_list
    """
    return ["\n" + line for line in input_list]


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
    with open(path, open_type) as f:
        f.writelines(add_linebreaks(lines))


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
