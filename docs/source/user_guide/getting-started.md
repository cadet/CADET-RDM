
# Getting started

## Initialize Project Repository

Create a new project repository or convert an existing repository into a CADET-RDM repo:

```bash
cadet-rdm initialize-repo <path-to-repo>
```

or from python

```python
from cadetrdm import initialize_repo

initialize_repo(path_to_repo)
```

The `output_folder_name` can be given optionally. It defaults to `output`.
