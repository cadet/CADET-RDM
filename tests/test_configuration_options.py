import numpy as np

from cadetrdm import Options


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


def test_excluded_keys():
    opt1 = Options()
    opt1["nested_dict"] = {"ba": "foo", "bb": "bar"}
    opt1.answer = 42
    opt1._n_cores = 9001

    opt2 = Options()
    opt2["nested_dict"] = {"ba": "foo", "bb": "bar"}
    opt2.answer = 42
    opt2._n_cores = 1

    assert opt1 == opt2
