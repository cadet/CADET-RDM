import hashlib
import json

from benedict import benedict
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


class Options(benedict):
    def __init__(self, *args, **kwargs):
        if "keyattr_dynamic" not in kwargs:
            kwargs["keyattr_dynamic"] = True
        super().__init__(*args, **kwargs)

    def dumps(self):
        return json.dumps(dict(self), cls=NumpyEncoder)

    @classmethod
    def loads(cls, string):
        decoded = json.loads(string, cls=NumpyDecoder)
        return cls(decoded)

    @classmethod
    def load_json_file(cls, file_path, **loader_kwargs):
        with open(file_path, "r") as handle:
            json_data = json.load(handle, cls=NumpyDecoder, **loader_kwargs)
        return cls(json_data)

    def dump_json_file(self, file_path, **dumper_kwargs):
        with open(file_path, "w") as handle:
            json.dump(dict(self), handle, cls=NumpyEncoder, **dumper_kwargs)

    def dump_json_str(self, **dumper_kwargs):
        return self.dumps()

    @classmethod
    def load_json_str(cls, string, **loader_kwargs):
        return cls.loads(string)

    @property
    def hash(self):
        excluded_keys = {"commit_message", "push", "debug"}
        remaining_keys = set(self.keys()) - excluded_keys
        remaining_dict = {key: self[key] for key in remaining_keys}
        dump = json.dumps(
            remaining_dict,
            cls=NumpyEncoder,
            ensure_ascii=False,
            sort_keys=True,
            indent=None,
            separators=(',', ':'),
        )

        hash_alphabet = "abcdefghjkmnpqrstvwxyz0123456789"
        hash_base = len(hash_alphabet)

        def to_base(number, base):
            result = ""
            while number:
                result += hash_alphabet[number % base]
                number //= base
            return result[::-1] or "0"

        base_16_hash = hashlib.sha1(dump.encode('utf-8')).hexdigest()
        base_10_hash = int(base_16_hash, 16)
        base_32_hash = to_base(base_10_hash, hash_base)

        return base_32_hash

    def __eq__(self, other):
        if not isinstance(other, Options):
            try:
                other = Options(other)
            except TypeError:
                print(f"TypeError when casting {other} to Options()")
                return NotImplemented

        return self.hash == other.hash


if __name__ == '__main__':
    options = Options()
    options.optimizer_options = 10
    options.commit_message = "Fuubar"
    options_rev = Options.load_json_str(options.dump_json_str())
    print(options.dump_json_str())
    options_rev.commit_message = "unfoo"
    print(options.__hash__(), options_rev.__hash__())
