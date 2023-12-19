
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

```commandline
mamba env create -f rdm_environment.yml
```

For use with [pip](https://pypi.org/project/pip/), create a rdm_requirements.txt file like:

```
python==3.11
cadet-rdm>=0.0.15
```

```commandline
pip install -r rdm_requirements.txt
```
