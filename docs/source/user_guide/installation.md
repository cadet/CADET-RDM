# Installation

CADET-RDM can be installed using:

```bash
pip install cadet-rdm
```

We strongly recommend using a dedicated environment to install CADET-RDM. See
[A guide to reproducible Python environments and CADET installations](https://forum.cadet-web.de/t/a-guide-to-reproducible-python-environments-and-cadet-installations/766)
for general background.

## Installation using conda or mamba

For use with [mamba](https://github.com/conda-forge/miniforge#mambaforge) or
[conda](https://docs.conda.io/projects/miniconda/en/latest/), create an environment file `rdm_environment.yml`:

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

Create the environment with:

```bash
conda env create -f rdm_environment.yml
```

## Installation using pip

For use with [pip](https://pypi.org/project/pip/), create a `rdm_requirements.txt` file:

```
python==3.11
cadet-rdm>=1.0.1
```

Install the dependencies with:

```bash
pip install -r rdm_requirements.txt
```

## Developer installation

To install a development version of CADET-RDM from source, clone the repository and install it in editable mode.

```bash
git clone git@github.com:cadet/CADET-RDM.git
cd CADET-RDM
pip install -e .
```

Cloning via SSH is recommended. Alternatively, HTTPS can be used with
`https://github.com/cadet/CADET-RDM.git`.


This installs CADET-RDM in editable mode, so local code changes take effect immediately without reinstalling the package. This setup is recommended for development, debugging, or contributing to CADET-RDM.


## Git LFS

Running CADET-RDM requires [Git LFS](https://git-lfs.com/), which must be installed separately.

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

  Download and install Git LFS from
  [https://git-lfs.com](https://git-lfs.com)


## Extending Git LFS scope

Several common data types are tracked with Git LFS by default:

```
*.jpg, *.png, *.xlsx, *.h5, *.ipynb, *.pdf, *.docx, *.zip, *.html
```

Additional file types can be added if required.

From Python:

```python
from cadetrdm import ProjectRepo

repo = ProjectRepo()
repo.output_repo.add_filetype_to_lfs("*.npy")
```

From the command line, run the following command inside the output repository:

```bash
rdm lfs add *.npy
```
