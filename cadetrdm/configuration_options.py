import json

from benedict import BeneDict, benedict_to_dict
import benedict.data_format as df
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return {"__class__": "numpy.ndarray", "value": obj.tolist()}
        return json.JSONEncoder.default(self, obj)


class NumpyDecoder(json.JSONDecoder):
    """Deserilize JSON object numpy arrays."""

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        import numpy
        if '__class__' not in obj:
            return obj
        match obj['__class__']:
            case 'numpy.ndarray':
                return numpy.array(obj['value'])
        return obj


class Options(BeneDict):
    def dumps(self):
        return json.dumps(benedict_to_dict(self), cls=NumpyEncoder)

    @classmethod
    def loads(cls, string):
        decoded = json.loads(string, cls=NumpyDecoder)
        return cls(decoded)

    @classmethod
    def load_json_file(cls, file_path, **loader_kwargs):
        return cls(df.load_json_file(file_path, cls=NumpyDecoder, **loader_kwargs))

    def dump_json_file(self, file_path, **dumper_kwargs):
        df.dump_json_file(benedict_to_dict(self), file_path, cls=NumpyEncoder, **dumper_kwargs)

    def dump_json_str(self, **dumper_kwargs):
        return self.dumps()

    @classmethod
    def load_json_str(cls, string, **loader_kwargs):
        return cls.loads(string)

    def __hash__(self):
        return self.dumps().__hash__()


if __name__ == '__main__':
    options = Options()
    options.commit_message = "Fuubar"
    options_rev = Options.load_json_str(options.dump_json_str())
