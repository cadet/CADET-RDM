import urllib.request
import shutil
import tempfile


def prepare_conda_env(url: str = None):
    if url is None:
        url = 'https://raw.githubusercontent.com/modsim/bug_report_example/master/conda_base_environment.yml'
    with urllib.request.urlopen(url) as response:
        with tempfile.NamedTemporaryFile(delete=False, prefix="environment_", suffix=".yaml") as tmp_file:
            shutil.copyfileobj(response, tmp_file)

    print("Please then run this command in a terminal (Linux) or anaconda shell (Windows):")
    print(f"conda env create -f {tmp_file.name}")
    return
