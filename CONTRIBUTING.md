# Contributing to CADET-RDM

This file covers the mechanics of working on CADET-RDM: development setup, code style, tests, documentation, and releases.
For user-facing installation and usage, see https://cadet-rdm.readthedocs.io.
If you need further guidance, you can find the team on the [CADET-Forum](https://forum.cadet-web.de/).


## Development setup

A dedicated conda environment is strongly recommended, since CADET-RDM inspects the active environment when recording run metadata.
Some tests run projects that depend on CADET-Process, which in turn needs CADET-Core from conda-forge:

```bash
conda create -n cadet-rdm -c conda-forge "python>=3.11" cadet pip
conda activate cadet-rdm
```

Clone the repository and install it in editable mode together with the development dependencies:

```bash
git clone git@github.com:cadet/CADET-RDM.git
cd CADET-RDM
pip install -e . --group dev
```

The `dev` group includes the `testing` and `docs` groups as well as ruff and pre-commit.
Install a single group, e.g. `--group testing`, if you only need part of it.
The `--group` flag requires pip 25.1 or newer.

Two things outside the Python environment are required before the test suite will pass.

Git LFS must be installed and initialized (`git lfs install`), because CADET-RDM tracks common data filetypes through LFS.
Installation instructions per platform are in the [user documentation](https://cadet-rdm.readthedocs.io/en/latest/user_guide/installation.html).

Git needs a global identity, because the tests create repositories and commit to them:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```


## Code style

CADET-RDM is linted with [ruff](https://docs.astral.sh/ruff/).
The rules are configured in `pyproject.toml`:

- pycodestyle (`E`, `W`) and pyflakes (`F`), with a maximum line length of 100 characters and 94 characters for docstrings and comments,
- docstrings (`D`) in the [numpy style](https://numpydoc.readthedocs.io/en/latest/format.html) for all public modules, classes, methods, and functions, starting with an imperative summary line,
- type annotations (`ANN`) for all function arguments and return values.

Tests are exempt from the docstring and annotation rules.
Use the ruff version pinned in the `dev` group, since the rules include preview rules that change between ruff versions:

```bash
ruff check
```

The `Ruff` GitHub workflow runs the same check on every pull request and fails on any violation.

### Pre-commit hooks

[pre-commit](https://pre-commit.com/) runs ruff together with checks for merge conflicts, YAML syntax, trailing whitespace, and missing final newlines before every commit.
Install the hooks once from the repository root:

```bash
pre-commit install
```

To run the hooks on all files, e.g. after changing the configuration:

```bash
pre-commit run --all-files
```


## Tests

The suite lives in `tests/` and runs under pytest.
Tests create real Git repositories in temporary directories, so they are slower and more side-effect-heavy than pure unit tests.

Three markers are defined in `pyproject.toml`:

- `slow` for long-running tests,
- `server_api` for tests that talk to the GitLab or GitHub API,
- unmarked tests, which need nothing beyond a local Git installation.

CI runs only the unmarked subset:

```bash
pytest tests -m "not server_api and not slow"
```

Run that selection locally before opening a pull request.
CI also measures test coverage with pytest-cov and uploads it to [Codecov](https://codecov.io/gh/cadet/CADET-RDM).
To see the coverage locally, add `--cov=cadetrdm --cov-report=term-missing` to the pytest call.
The marked subsets require credentials or network access and are expected to be run deliberately, not by default.

The `server_api` tests create and delete repositories through the GitLab and GitHub APIs.
They read a Personal Access Token from the Python keyring, stored under the URL of the instance and your username:

```bash
keyring set "https://jugit.fz-juelich.de/" <username>
```

On GitHub, create a fine-grained token with

- *Repository access* set to *All repositories*, and
- the repository permission *Administration* set to *Read and write*,

so that it can create and delete repositories.
On GitLab, the token needs the `api` scope.

Tests are executed on Ubuntu against Python 3.11, 3.12, and 3.13, plus one Windows and one macOS job on 3.13.
The minimum supported Python version is 3.11.


## Documentation

The documentation source is Sphinx with MyST markdown under `docs/source`, published to Read the Docs.

```bash
pip install -e . --group docs
cd docs
sphinx-build -b html source build
```

The rendered output is in `docs/build` and can be opened in any browser.
User-facing behavior changes should be reflected in `docs/source/user_guide` in the same pull request that changes the behavior.


## Issues and pull requests

GitHub issues are used to report bugs, suggest features, and discuss technical problems.
When reporting a bug, describe how to reproduce it and include the CADET-RDM version and the traceback.

Pull requests should be submitted once the changes are complete and tested.
Keep each pull request to one issue or feature and reference the related issues in the description.


## Branches and commits

Work happens on feature branches that are opened as pull requests against `main`.
Base new work on `main` and ask if in doubt.
CI runs the test stage on pull requests against any branch, and on pushes to `main` and `dev`.

Branch names follow the [conventional branch](https://conventional-branch.github.io/) convention:

- `feature/` for new features, e.g. `feature/add-remote-command`,
- `fix/` for bug fixes, e.g. `fix/case-load-read-only`,
- `release/` for branches preparing a release, e.g. `release/v1.2.0`,
- `chore/` for non-code tasks such as dependency and documentation updates.

Commit subjects are short and imperative, optionally prefixed with the area of the change (`Docs:`, `Fix:`, `Feat:`, `Tests:`, `CI:`).
The subject says what changed; the body, where one is needed, says why.


## Releases

CADET-RDM follows [semantic versioning](https://semver.org/) and is released from `main` to PyPI.
To make a release, open an issue from the *Release checklist* template and work through it.
In short:

1. Bump the version in `cadetrdm/__init__.py` and in `.zenodo.json` (title and version).
   The package version is read from `__version__`, so `cadetrdm/__init__.py` is the single source of truth for the package.
2. Merge the version bump into `main`.
3. Publish a GitHub release with the tag `vX.Y.Z` and release notes.

Publishing the release triggers `.github/workflows/release.yml`, which builds the distributions and uploads them to PyPI through trusted publishing.
The workflow deliberately triggers on published releases rather than on tags, to avoid running twice for a single release.
Zenodo archives each GitHub release and assigns it a version-specific DOI.


## License

CADET-RDM is licensed under the [GNU General Public License v3](LICENSE).
By contributing, you agree that your contributions are licensed under the same terms.
