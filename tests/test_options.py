import numpy as np

from cadetrdm import Options
from cadetrdm.options import remove_invalid_keys


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


def test_options_file_io():
    opt = Options()
    opt["array"] = np.linspace(0, 2, 200)
    opt["nested_dict"] = {"ba": "foo", "bb": "bar"}
    initial_hash = opt.get_hash()
    opt.dump_json_file("options.json")
    opt_recovered = Options.load_json_file("options.json")
    post_serialization_hash = opt_recovered.get_hash()
    assert initial_hash == post_serialization_hash
    assert opt == opt_recovered


def test_remove_keys_starting_with_underscore():
    input_dict = {
        "_private": 1,
        "valid": 2,
        "__magic__": 3
    }
    expected = {"valid": 2}
    assert remove_invalid_keys(input_dict) == expected


def test_remove_keys_containing_double_underscore():
    input_dict = {
        "normal": 1,
        "with__double": 2,
        "another": 3
    }
    expected = {"normal": 1, "another": 3}
    assert remove_invalid_keys(input_dict) == expected


def test_nested_dict_removal():
    input_dict = {
        "level1": {
            "_invalid": 1,
            "valid": {
                "__still_invalid__": 2,
                "ok": 3
            }
        },
        "__should_be_removed__": "nope"
    }
    expected = {
        "level1": {
            "valid": {
                "ok": 3
            }
        }
    }
    assert remove_invalid_keys(input_dict) == expected


def test_empty_dict():
    assert remove_invalid_keys({}) == {}


def test_all_invalid_keys():
    input_dict = {
        "_one": 1,
        "__two__": 2,
        "with__double": 3
    }
    assert remove_invalid_keys(input_dict) == {}


def test_no_invalid_keys():
    input_dict = {
        "a": 1,
        "b": {
            "c": 2
        }
    }
    assert remove_invalid_keys(input_dict) == input_dict

def test_explicit_invalid_keys():
    input_dict = {
        "a": 1,
        "b": {
            "c": 2
        }
    }
    expected = {
        "b": {
            "c": 2
        }
    }
    assert remove_invalid_keys(input_dict, excluded_keys=["a"]) == expected
