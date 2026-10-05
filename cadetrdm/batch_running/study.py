import os
import warnings
from typing import Any

from cadetrdm import ProjectRepo


class Study(ProjectRepo):
    """Deprecated alias of ProjectRepo."""

    def __init__(
        self,
        path: os.PathLike,
        url: str | None = None,
        branch: str | None = None,
        name: str | None = None,
        suppress_lfs_warning: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            path=path,
            url=url,
            suppress_lfs_warning=suppress_lfs_warning,
            branch=branch,
            *args,
            **kwargs,
        )
        warnings.warn(
            "cadetrdm.Study() will be deprecated soon. Please use ProjectRepo()",
            FutureWarning
        )
