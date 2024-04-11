from pathlib import Path

import pytest

from cadetrdm.batch_runner import Study


@pytest.mark.server_api
def test_module_import():
    WORK_DIR = Path.cwd() / "tmp"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    puetmann2013 = Study(
        WORK_DIR / 'puetmann2013',
        "git@jugit.fz-juelich.de:r.jaepel/puetmann2013.git",
    )

    assert hasattr(puetmann2013.module, "main")
    assert hasattr(puetmann2013.module, "setup_optimization_problem")
