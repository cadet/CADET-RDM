import urllib.request
import shutil
import tempfile


def prepare_conda_env(url: str = None):
    if url is None:
        url = 'https://raw.githubusercontent.com/modsim/bug_report_example/master/conda_base_environment.yml'
        print("Using default environment configuration from")
        print(url)
    with urllib.request.urlopen(url) as response:
        with tempfile.NamedTemporaryFile(delete=False, prefix="environment_", suffix=".yaml") as tmp_file:
            shutil.copyfileobj(response, tmp_file)

    print("Please now run this command in a terminal (Linux) or anaconda shell (Windows):\n")
    print(f"conda deactivate && conda env create -f {tmp_file.name}\n")
    return
