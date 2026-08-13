# Contributing to CADET-RDM

This file covers the mechanics of working on CADET-RDM: development setup, tests, documentation, and releases.
For what the project is and where it is going, see [PROJECT.md](PROJECT.md).
For user-facing installation and usage, see https://cadet-rdm.readthedocs.io.


## Development setup

Clone the repository and install it in editable mode together with the testing dependencies:

```bash
git clone git@github.com:cadet/CADET-RDM.git
cd CADET-RDM
pip install -e . --group testing
```

The `--group` flag requires pip 25.1 or newer.
A dedicated conda or virtual environment is strongly recommended, since CADET-RDM inspects the active environment when recording run metadata.

Two things outside the Python environment are required before the test suite will pass.

Git LFS must be installed and initialized (`git lfs install`), because CADET-RDM tracks common data filetypes through LFS.
Installation instructions per platform are in the [user documentation](https://cadet-rdm.readthedocs.io/en/latest/user_guide/installation.html).

Git needs a global identity, because the tests create repositories and commit to them:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```


## Tests

The suite lives in `tests/` and runs under pytest.
Tests create real Git repositories in temporary directories, so they are slower and more side-effect-heavy than pure unit tests.

Four markers are defined in `pyproject.toml`:

- `slow` for long-running tests,
- `server_api` for tests that talk to the GitLab or GitHub API,
- `container` for tests that require Docker, Podman, or Apptainer,
- unmarked tests, which need nothing beyond a local Git installation.

CI runs only the unmarked subset:

```bash
pytest tests -m "not server_api and not container and not slow"
```

Run that selection locally before opening a pull request.
The marked subsets require credentials or a container runtime and are expected to be run deliberately, not by default.

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


## Branches and pull requests

Work happens on feature branches that are opened as pull requests.
CI runs the test stage on pull requests against any branch, and on pushes to `main` and `dev`.

Until its fate is settled, base new work on `main` and ask if in doubt.

Commit subjects are short and imperative, optionally prefixed with the area of the change (`Docs:`, `Fix:`, `Feat:`, `Tests:`, `CI:`).
The subject says what changed; the body, where one is needed, says why.


## Releases

Releases are published to PyPI from GitHub.

1. Bump `__version__` in `cadetrdm/__init__.py`.
   The package version is read from that attribute, so it is the single source of truth.
2. Update `.zenodo.json` if authorship or metadata changed.
3. Commit, tag as `vX.Y.Z`, and push the tag.
4. Publish a GitHub release for the tag.

Publishing the release triggers `.github/workflows/release.yml`, which builds the distributions and uploads them to PyPI through trusted publishing.
The workflow deliberately triggers on published releases rather than on tags, to avoid running twice for a single release.
