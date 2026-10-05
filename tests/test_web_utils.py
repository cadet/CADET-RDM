from pathlib import Path

from cadetrdm.web_utils import ssh_url_to_http_url


def test_ssh_url_to_http_url():
    assert (
        ssh_url_to_http_url("git@jugit.fz-juelich.de:IBG-1/ModSim/cadet/rdm_example.git")
        == "https://jugit.fz-juelich.de/IBG-1/ModSim/cadet/rdm_example"
    )
    assert ssh_url_to_http_url("https://github.com/cadet/CADET-RDM") == "https://github.com/cadet/CADET-RDM"


def test_ssh_url_to_http_url_accepts_local_path(tmp_path):
    assert ssh_url_to_http_url(tmp_path) == str(tmp_path)
    assert ssh_url_to_http_url(Path("..") / "repo") == str(Path("..") / "repo")
