import re
import uuid

import numpy as np
import pytest

from cadetrdm import initialize_repo
from cadetrdm import Options
from cadetrdm.options import remove_invalid_keys
from cadetrdm import ProjectRepo


@pytest.fixture
def clean_repo(tmp_path):
    """Fixture to initialize and clean up a test repository."""
    repo_path = tmp_path / "test_repo_cli"
    initialize_repo(repo_path)
    repo = ProjectRepo(repo_path)
    yield repo


def test_options_hash():
    opt = Options()
    opt["array"] = np.linspace(2, 200)
    opt["nested_dict"] = {"ba": "foo", "bb": "bar"}
    initial_hash = opt.get_hash()
    s = opt.dumps()
    opt_recovered = Options.loads(s)
    post_serialization_hash = opt_recovered.get_hash()
    assert initial_hash == post_serialization_hash
    assert opt == opt_recovered


def test_options_file_io(tmp_path):
    opt = Options()
    opt["array"] = np.linspace(0, 2, 200)
    opt["nested_dict"] = {"ba": "foo", "bb": "bar"}
    initial_hash = opt.get_hash()
    opt.dump_json_file(tmp_path / "options.json")
    opt_recovered = Options.load_json_file(tmp_path / "options.json")
    post_serialization_hash = opt_recovered.get_hash()
    assert initial_hash == post_serialization_hash
    assert opt == opt_recovered


@pytest.mark.parametrize(
    "input_dict, expected",
    [
        ({"_private": 1, "valid": 2, "__magic__": 3}, {"valid": 2}),
        (
            {
                "level1": {
                    "_invalid": 1,
                    "valid": {"__still_invalid__": 2, "ok": 3},
                },
                "__should_be_removed__": "nope",
            },
            {"level1": {"valid": {"ok": 3}}},
        ),
        ({}, {}),
        ({"_one": 1, "__two__": 2, "with__double": 3}, {}),
        ({"a": 1, "b": {"c": 2}}, {"a": 1, "b": {"c": 2}}),
    ],
    ids=[
        "keys_starting_with_underscore",
        "nested_dict_removal",
        "empty_dict",
        "all_invalid_keys",
        "no_invalid_keys",
    ],
)
def test_remove_invalid_keys(input_dict, expected):
    assert remove_invalid_keys(input_dict) == expected


def test_remove_explicit_invalid_keys():
    input_dict = {"a": 1, "b": {"c": 2}}
    expected = {"b": {"c": 2}}
    assert remove_invalid_keys(input_dict, excluded_keys=["a"]) == expected


def test_branch_name(clean_repo):
    options = Options()
    options.commit_message = "Commit Message Test"
    options.debug = True
    options.push = False
    options.source_directory = "src"

    hash = str(clean_repo.head.commit)[:7]
    active_branch = str(clean_repo.active_branch)
    new_branch = clean_repo.get_new_output_branch_name()

    escaped_branch = re.escape(active_branch)
    pattern = rf"^\d{{4}}-\d{{2}}-\d{{2}}_\d{{2}}-\d{{2}}-\d{{2}}_{escaped_branch}_{hash}_[0-9a-f]{{6}}$"
    assert re.match(pattern, new_branch), f"Branch name '{new_branch}' does not match expected format"


def test_branch_name_with_prefix(clean_repo):
    options = Options()
    options.commit_message = "Commit Message Test"
    options.debug = True
    options.push = False
    options.source_directory = "src"
    options.branch_prefix = "Test_Prefix"

    hash = str(clean_repo.head.commit)[:7]
    active_branch = str(clean_repo.active_branch)
    new_branch = clean_repo.get_new_output_branch_name(options.branch_prefix)

    escaped_branch = re.escape(active_branch)
    pattern = rf"^Test_Prefix_\d{{4}}-\d{{2}}-\d{{2}}_\d{{2}}-\d{{2}}-\d{{2}}_{escaped_branch}_{hash}_[0-9a-f]{{6}}$"
    assert re.match(pattern, new_branch), f"Branch name '{new_branch}' does not match expected format"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
