
# Installation

CADET-RDM can be installed using

```pip install cadet-rdm```

We *highly* recommend using an
[environment file](https://forum.cadet-web.de/t/a-guide-to-reproducible-python-environments-and-cadet-installations/766)
to install CADET-RDM.

For use with [mamba](https://github.com/conda-forge/miniforge#mambaforge) or
[conda](https://docs.conda.io/projects/miniconda/en/latest/), create a rdm_environment.yml like:

```yaml
name: rdm_example
channels:
  - conda-forge
dependencies:
  - python=3.11
  - conda
  - pip
  - pip:
      - cadet-rdm
```

and then run

```bash
mamba env create -f rdm_environment.yml
```

For use with [pip](https://pypi.org/project/pip/), create a rdm_requirements.txt file like:

```
python==3.11
cadet-rdm>=0.0.15
```

```bash
pip install -r rdm_requirements.txt
```


## Git-LFS
Running `cadet-rdm` requires [**Git LFS**](https://git-lfs.com/), which needs to be installed separately.

* **Ubuntu/Debian**:
  ```bash
  sudo apt-get install git-lfs
   git lfs install
  ```

 * **macOS** (with Homebrew):

   ```bash
   brew install git-lfs
   git lfs install
   ```

 * **Windows**:
   Download and install from [https://git-lfs.com](https://git-lfs.com)



## Extending GIT-LFS scope

Several common datatypes are included in GIT-LFS by default. These currently are
`"*.jpg", "*.png", "*.xlsx", "*.h5", "*.ipynb", "*.pdf", "*.docx", "*.zip", "*.html"`

Additional datatypes can be added if required by running:

````python
from cadetrdm import ProjectRepo

repo = ProjectRepo()

repo.output_repo.add_filetype_to_lfs("*.npy")
````


or from within the output directory in a command line:

```bash
rdm lfs add *.npy
```