# CADET-RDM Documentation

To build the documentation locally, install sphinx and other dependencies by running

```
pip install -e .[docs]
```
from the CADET-RDM root directory.

Then, in the `docs` folder run:

```
sphinx-build -b html source build
```

The output is in the `build` directory and can be opened with any browser.
