
# Jupyter interface

The CADET-RDM Jupyter interface **only works** with [Jupyter Lab](https://jupyterlab.readthedocs.io/en/latest/), 
and not with the old [Jupyter Notebook](https://jupyter-notebook.readthedocs.io/en/stable/notebook.html) interface
at the moment.

## General concepts

### Jupytext

Jupyter Notebooks are not well suited for version control with git, as the metadata and cell outputs are stored besides 
the input code. This overwhelms the inspection of differences within commits and the comparisons between branches. 

Therefore, the [jupytext](https://github.com/mwouts/jupytext) extension is used by default to convert `.ipynb` files
into a `.py` files, with the markdown cells included as block comments. All `.ipynb` files are removed from git's 
version control through the `.gitignore` file and only changes in the `.py` files are tracked. The `.py` files are
automatically created and updated whenever a `.ipynb` file is saved. 

Please ensure, that `juyptext` is working for you and that a `.py` file is created after saving your notebook, otherwise
your code will not be version-controlled.

### Reproducibility

To ensure results from `.ipynb` files are perfectly reproducible, `CADET-RDM` does not allow for the tracking of
results generated during live-coding usage. Therefore, before committing results, 
all previous outputs are cleared and all cells
are executed sequentially from top to bottom and then committed to the output repository.

To maintain the link between Markdown annotation, code, and inline graphs, the final notebook is also saved as
a `.html` webpage into the output folder for future inspection.

## Tracking Results

To use `CADET-RDM` from within an `.ipynb` file, please include this at the top of your file.

```python
from cadetrdm.repositories import JupyterInterfaceRepo

repo = JupyterInterfaceRepo()
```

Then, at the end of your file, run:
```python
repo.commit_nb_output(
    "path-to-the-current-notebook.ipynb",
    results_commit_message="Results commit message"
)
```

This will re-run the `.ipynb` file from the start, save a html version of the completed notebook into the output repo
and commit all changes to the output repo.

## Committing changes to your code

You can commit all current changes to your code directly from Jupyter by running

```python
from cadetrdm.repositories import JupyterInterfaceRepo

repo = JupyterInterfaceRepo()

repo.commit("Commit message")
```

## Other workflows

All other workflows function identically as described in the {ref}`python_interface` section.