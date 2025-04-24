import warnings

from cadetrdm import ProjectRepo


class Study(ProjectRepo):
    def __init__(self, path, url=None, branch=None, name=None, suppress_lfs_warning=False, *args, **kwargs):
        super().__init__(path=path, url=url, suppress_lfs_warning=suppress_lfs_warning, branch=branch, *args, **kwargs)
        warnings.warn(
            "cadetrdm.Study() will be deprecated soon. Please use ProjectRepo()",
            FutureWarning
        )
