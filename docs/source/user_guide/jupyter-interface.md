# Jupyter interface

The CADET-RDM Jupyter interface provides integration with JupyterLab for tracking code and results generated from notebooks.

At the moment, the Jupyter interface **only works** with [Jupyter Lab](https://jupyterlab.readthedocs.io/en/latest/),
and not with the classic [Jupyter Notebook](https://jupyter-notebook.readthedocs.io/en/stable/notebook.html) interface.

## Overview and concepts

The Jupyter interface builds on the Python interface and applies additional constraints to ensure reproducibility when working with notebooks.

### Jupytext

Jupyter notebooks are not well suited for version control with Git, as metadata and cell outputs are stored alongside the input code. This makes inspecting changes and comparing branches difficult.

Therefore, CADET-RDM uses the [jupytext](https://github.com/mwouts/jupytext) extension by default. Notebooks are converted from `.ipynb` files into `.py` files, with Markdown cells stored as block comments.

* `.ipynb` files are excluded from version control via `.gitignore`
* only the generated `.py` files are tracked in Git
* the `.py` file is automatically created and updated whenever the notebook is saved

Please ensure that `jupytext` is working correctly and that a `.py` file is generated when saving the notebook. Otherwise, code changes will not be version controlled.

### Reproducibility

To ensure that results generated from notebooks are reproducible, CADET-RDM does not allow tracking results produced during interactive execution.

Before committing results:

* all existing outputs are cleared
* all cells are executed sequentially from top to bottom
* the executed notebook is committed to the output repository



## Handling results with CADET-RDM

### Tracking results from notebooks

To use CADET-RDM inside a Jupyter notebook, initialize the repository interface at the top of the notebook:

```python
from cadetrdm.repositories import JupyterInterfaceRepo

repo = JupyterInterfaceRepo()
```

At the end of the notebook, trigger result tracking and committing:

```python
repo.commit_nb_output(
    "path-to-the-current-notebook.ipynb",
    results_commit_message="Results commit message"
)
```

This will:

* re-run the notebook from the beginning
* commit all generated results to a new output branch
* save a html and ipynb version of the current notebook inside the output branch. The parameter `conversion_formats` can be used to specify the desired output format of the notebook. It defaults to `["html", "ipynb"]`.

### Committing code changes

Code changes can be committed directly from within Jupyter:

```python
from cadetrdm.repositories import JupyterInterfaceRepo

repo = JupyterInterfaceRepo()
repo.commit("Commit message")
```


## Other workflows

All other workflows, including:

* reusing results from earlier runs
* importing results from other repositories
* configuring remotes
* pushing results
* cloning repositories

behave identically to the Python interface and are described in the {ref}`python_interface` section.