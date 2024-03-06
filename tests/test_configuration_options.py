import numpy as np

from cadetrdm import Options


def test_options_hash():
    opt = Options()
    opt["array"] = np.linspace(2, 200)
    opt["nested_dict"] = {"ba": "foo", "bb": "bar"}
    initial_hash = hash(opt)
    s = opt.dumps()
    opt_recovered = Options.loads(s)
    post_serialization_hash = hash(opt_recovered)
    assert initial_hash == post_serialization_hash


def test_options_file_io():
    opt = Options()
    opt["array"] = np.linspace(0, 2, 200)
    opt["nested_dict"] = {"ba": "foo", "bb": "bar"}
    initial_hash = hash(opt)
    opt.dump_json_file("options.json")
    opt_recovered = Options.load_json_file("options.json")
    post_serialization_hash = hash(opt_recovered)
    assert initial_hash == post_serialization_hash