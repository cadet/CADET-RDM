import os
import time
from datetime import datetime
from pathlib import Path

import pytest

from cadetrdm import Options, Study, Case
from cadetrdm.io_utils import delete_path


@pytest.mark.server_api
def test_module_import():
    WORK_DIR = Path.cwd() / "tmp"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    rdm_example = Study(
        WORK_DIR / 'template',
        "git@jugit.fz-juelich.de:r.jaepel/rdm_example.git",
    )

    assert hasattr(rdm_example.module, "main")
    assert hasattr(rdm_example.module, "setup_optimization_problem")

    delete_path(WORK_DIR)
