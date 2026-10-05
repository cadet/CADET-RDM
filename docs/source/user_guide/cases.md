(cases)=
# Cases

CADET-RDM identifies every result by the combination of three things:

- the **project**: the commit of the project repository that produced the result,
- the **options**: the configuration the project code was run with,
- the **environment**: the conda and pip packages installed during the run.

A `Case` bundles a project repository with a set of `Options` and, optionally, `Environment` requirements.
It runs the project code for this combination, or reuses existing results if this combination was already run.
This makes parameter studies and comparisons reproducible without manual bookkeeping of which result belongs to which configuration.

## Options

`Options` is a nested dictionary that also supports attribute access.
It holds the configuration of a run and is stored as `options.json` with the results.

```python
from cadetrdm import Options

options = Options()
options.commit_message = "Parameter study, high flow rate"
options.debug = False
options.push = True
options.flow_rate = 2.5e-7
options.optimizer_options = {"optimizer": "U_NSGA3", "pop_size": 16}
```

Values must be JSON-serializable: Python built-ins, numpy arrays and `pathlib.Path` objects are supported.
Options can be saved and loaded with `options.dump_json_file(path)` and `Options.load_json_file(path)`.

### The options hash

Each set of options has a hash, `options.get_hash()`, which identifies the configuration in the output log.
Not every key contributes to the hash:

- The run control keys `commit_message`, `debug`, `push`, `force` and `branch_prefix` are excluded, since they do not change the result.
- Keys starting with an underscore (`_`) or containing a double underscore (`__`) are excluded at every nesting level.
  Use them for machine-specific settings that should not affect the identity of a result, e.g. a temporary directory:

```python
options._tmp_directory = "/dev/shm"
```

### Reusing options

Because the hash depends only on the configuration, the same `Options` can be reused across projects, e.g. to run the same parameter set with different models, or copied and modified for a parameter study:

```python
cases = []
for flow_rate in [1.0e-7, 2.5e-7, 5.0e-7]:
    case_options = options.copy()
    case_options.flow_rate = flow_rate
    cases.append(case_options)
```

## Environments

An `Environment` describes package requirements.
Package versions are given as exact versions or as [semantic version](https://semver.org/) specifications:

```python
from cadetrdm import Environment

environment = Environment(
    conda_packages={"cadet": ">=5.0.3"},
    pip_packages={"cadet-process": "~0.12.0", "numpy": "2.0.2"},
)
```

- `"2.0.2"` requires exactly this version.
- `">=5.0.3"`, `"<6"` and similar require a version in this range.
- `"~0.12.0"` requires an approximately matching version, i.e. `0.12.x`.

For every run, CADET-RDM records the complete environment (`conda env export` and `pip freeze`) in the `run_history` directory on the main branch of the output repository.
An `Environment` given to a `Case` is checked against these records, so only results created in a matching environment are reused.
CADET-RDM does not install packages: if the active environment does not fulfil the requirements, the case is not run.

## Preparing the project for cases

A `Case` imports the main package of the project repository and calls its `main` function, or the function given with `Case(..., run_method=...)`.
By default, the package is the directory named like the project repository, e.g. `my_project/my_project/__init__.py`, and a different directory can be set with `ProjectRepo(package_dir=...)`.
The function is decorated with `tracks_results`, which runs it in the tracking context and passes the project repository and the options:

```python
# my_project/my_project/main.py
from cadetrdm import tracks_results


@tracks_results
def main(repo, options):
    results = simulate(flow_rate=options.flow_rate)
    results.save(repo.output_path / "results.h5")
```

```python
# my_project/my_project/__init__.py
from .main import main
```

The decorated function can also be called directly with options, a dictionary or the path to an options JSON file.
It requires the keys `commit_message` and `debug`, writes the options to `options.json` in the output, pushes the results if `options.push` is set, and returns the name of the new output branch together with the return value of the function.
With `options.debug = True`, the function runs without tracking the results.

## Running and loading cases

```python
from cadetrdm import Case, ProjectRepo

project_repo = ProjectRepo("path/to/my_project")
case = Case(project_repo=project_repo, options=options, environment=environment)

results_path = case.run_study()
```

`run_study()`

1. updates the project and output repositories from their remotes (skipped in debug mode),
2. looks for existing results of this project commit, these options and this environment,
3. returns the path to these results if they exist,
4. otherwise runs the project code, if the active environment fulfils the environment requirements, and returns the path to the new results.

Use `run_study(force=True)` to run the code even if results exist.
If the code fails or the environment does not match, `run_study()` returns `None`.
The execution status is stored in a `<project>.status` file next to the project repository, so a case that is already running elsewhere on the same file system is skipped.

To only look up existing results without running anything, use `load()`:

```python
results_path = case.load()

case.has_results_for_this_run
case.results_branch
```

`load()` does not modify the project or output repository.
It reads the output log from the local main branch of the output repository, so results that were pushed from another machine are only found after updating, e.g. with `run_study()` or `case.output_repo.update_main()`.

By default, results must match the project commit, the options hash and the environment.
Each requirement can be relaxed, e.g. to reuse results from an earlier commit whose changes do not affect them:

```python
results_path = case.load(
    allow_commit_hash_mismatch=True,
    allow_options_hash_mismatch=False,
    allow_environment_mismatch=False,
)
```

## Results are unique and read-only

Every run creates its own output branch, named after the time of the run, the project branch and commit, plus a random suffix (see {ref}`Python interface <python_interface>`).
A result therefore always points to exactly one project commit, one set of options and one recorded environment, and can be reproduced by checking out that commit and running it again with the stored `options.json`.

Loaded results are copied into the cache directory `<output>_cached/<branch name>` of the project repository and made read-only, so a result that is used as input for further work cannot be modified by accident.
