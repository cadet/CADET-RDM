import importlib
import os
import sys
from pathlib import Path

from cadetrdm import ProjectRepo, clone


class Study(ProjectRepo):
    def __init__(self, path, url, branch="main", name=None, *args, **kwargs):
        if name is None:
            self.name = Path(path).parts[-1]
        else:
            self.name = name
        self.url = url

        try:
            if not path.exists():
                clone(self.url, path)
            ProjectRepo(path).checkout(branch)
        except Exception as e:
            raise Exception(f"Error processing study {self.name}") from e

        super().__init__(path, *args, **kwargs)

    @property
    def module(self):
        cur_dir = os.getcwd()

        os.chdir(self.path)
        sys.path.append(str(self.path))
        module = importlib.import_module(self.name)

        sys.path.remove(str(self.path))
        os.chdir(cur_dir)
        return module
