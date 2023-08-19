import urllib.request
import shutil
import tempfile

import click


@click.command()
@click.option('--url', default=None,
              help='Url to the environment.yml file.')
def prepare_conda_env_cli(url):
    prepare_conda_env(url)


def prepare_conda_env(url: str = None):
    if url is None:
        url = 'https://raw.githubusercontent.com/modsim/bug_report_example/master/conda_base_environment.yml'
    with urllib.request.urlopen(url) as response:
        with tempfile.NamedTemporaryFile(delete=False, prefix="environment_", suffix=".yaml") as tmp_file:
            shutil.copyfileobj(response, tmp_file)

    print("Please now run this command in a terminal (Linux) or anaconda shell (Windows):\n")
    print(f"conda env create -f {tmp_file.name}\n")
    return
