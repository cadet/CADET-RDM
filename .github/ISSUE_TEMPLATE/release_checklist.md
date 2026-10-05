---
name: Release checklist
about: Checklist to make a release
title: 'Release vX.X.X'
labels: 'maintenance'
assignees: ''

---

# CADET-RDM Release Checklist

CADET-RDM follows the semantic versioning system described at [semver.org](https://semver.org/).

CADET-RDM is released from the `main` branch and deployed to PyPI via a GitHub workflow automatically.

The following checklist describes the steps to execute sequentially for creating a new release.

---

## Preparation

- [ ] Ensure that CI passes on `main`, including the `Ruff` workflow.
- [ ] Create a release branch `release/vX.X.X` from `main`.
- [ ] Create a version bump commit `Bump version to vX.X.X`:
  - Update the version number in
  - `cadetrdm/__init__.py`
  - `.zenodo.json` (two places: `title` and `version`)
- [ ] Update `.zenodo.json` if authorship or other metadata changed.
- [ ] Run the tests that CI does not run, which need network access and API tokens
  (see *Tests* in `CONTRIBUTING.md` for the required environment variables and tokens):
  ```bash
  pytest tests -m "slow or server_api"
  ```
- [ ] Open a pull request from the release branch onto `main` and merge it.

---

## Creating the release on GitHub

- [ ] Go to [GitHub Releases](https://github.com/cadet/CADET-RDM/releases/new):
  - Set `main` as the target
  - Specify the tag `vX.X.X` according to semantic versioning
  - Add release notes with sections for Added, Fixed, Changed, and Updated
  - Publish the release.
- [ ] Verify Zenodo archiving:
  - Confirm that a version-specific DOI was created
  - Ensure that the source code and associated files are archived
  - Note that the [concept DOI](https://doi.org/10.5281/zenodo.14192517) remains constant

## Deployment on PyPI

- [ ] Check if the GitHub action with workflow file `release.yml` ran successfully, fix if required.
- [ ] Check the new version on the [PyPI CADET-RDM website](https://pypi.org/project/CADET-RDM/).
- [ ] Check that the [documentation](https://cadet-rdm.readthedocs.io) was built for the new version.

---

## Follow-up
- [ ] If this release checklist was updated, add these changes to the corresponding issue template
