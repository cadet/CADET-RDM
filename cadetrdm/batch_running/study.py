from functools import wraps
import warnings

from cadetrdm import ProjectRepo


class Study(ProjectRepo):
    @wraps(ProjectRepo.__init__)
    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        warnings.warn(
            "cadetrdm.Study() will be deprecated soon. Please use ProjectRepo()",
            FutureWarning
        )
