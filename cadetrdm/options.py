import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Self

from addict import Dict
import numpy as np


def remove_invalid_keys(dicti: dict, excluded_keys: Iterable[str] | None = None) -> dict:
    """
    Remove private, dunder and excluded keys from a nested dictionary.

    Excluded keys are only removed from the top level.

    Parameters
    ----------
    dicti : dict
        Dictionary to filter.
    excluded_keys : Iterable[str] | None, optional
        Keys to remove in addition to private and dunder keys.

    Returns
    -------
    dict
        Filtered copy of the dictionary.
    """
    if excluded_keys is None:
        excluded_keys = []

    def is_valid(key: str) -> bool:
        return not (key.startswith("_") or "__" in key or key in excluded_keys)

    new_dicti = {}
    for key, value in dicti.items():
        if not is_valid(key):
            continue
        if isinstance(value, dict):
            value = remove_invalid_keys(value)
        new_dicti[key] = value

    return new_dicti


class CustomEncoder(json.JSONEncoder):
    """Custom encoder to serialize additional types (e.g. numpy arrays) to json."""

    def default(self, obj: Any) -> Any:
        """
        Encode numpy arrays and paths as tagged dictionaries.

        Parameters
        ----------
        obj : Any
            Object that the default encoder can not serialize.

        Returns
        -------
        Any
            JSON-serializable representation of the object.
        """
        if isinstance(obj, np.ndarray):
            return {"__class__": "numpy.ndarray", "value": obj.tolist()}
        elif isinstance(obj, Path):
            return {"__class__": "Path", "value": obj.as_posix()}
        return json.JSONEncoder.default(self, obj)


class CustomDecoder(json.JSONDecoder):
    """Custom decoder to deserialize additional types (e.g. numpy arrays) from json."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj: dict) -> Any:
        """
        Decode tagged dictionaries written by CustomEncoder.

        Parameters
        ----------
        obj : dict
            Decoded JSON object.

        Returns
        -------
        Any
            Numpy array or path for tagged objects, else the unchanged dictionary.
        """
        import numpy
        if '__class__' not in obj:
            return obj
        match obj['__class__']:
            case 'numpy.ndarray':
                return numpy.array(obj['value'])
            case 'Path':
                return Path(obj['value'])
        return obj


class Options(Dict):
    """Nested dictionary of run options with attribute access and a stable hash."""

    def dumps(self) -> str:
        """
        Serialize the options to a JSON string.

        Returns
        -------
        str
            JSON representation of the options.
        """
        return json.dumps(dict(self), cls=CustomEncoder)

    def copy(self) -> Self:
        """
        Return a shallow copy of the options.

        Returns
        -------
        Options
            Copy of the options.
        """
        new = super().copy()
        return Options(new)

    # super.update() already takes care of nested dictionaries, so we don't have to

    @classmethod
    def loads(cls, string: str) -> Self:
        """
        Create options from a JSON string.

        Parameters
        ----------
        string : str
            JSON representation of the options.

        Returns
        -------
        Options
            Decoded options.
        """
        decoded = json.loads(string, cls=CustomDecoder)
        return cls(decoded)

    @classmethod
    def load_json_file(cls, file_path: str | Path, **loader_kwargs: Any) -> Self:
        """
        Create options from a JSON file.

        Parameters
        ----------
        file_path : str | Path
            Path to the JSON file.
        **loader_kwargs : Any
            Keyword arguments passed to json.load.

        Returns
        -------
        Options
            Decoded options.
        """
        with open(file_path, "r", encoding="utf-8") as handle:
            json_data = json.load(handle, cls=CustomDecoder, **loader_kwargs)
        return cls(json_data)

    def dump_json_file(self, file_path: str | Path, **dumper_kwargs: Any) -> None:
        """
        Write the options to a JSON file.

        Parameters
        ----------
        file_path : str | Path
            Path to the JSON file.
        **dumper_kwargs : Any
            Keyword arguments passed to json.dump.
        """
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(dict(self), handle, cls=CustomEncoder, **dumper_kwargs)

    def dump_json_str(self, **dumper_kwargs: Any) -> str:
        """
        Serialize the options to a JSON string.

        Parameters
        ----------
        **dumper_kwargs : Any
            Ignored.

        Returns
        -------
        str
            JSON representation of the options.
        """
        return self.dumps()

    @classmethod
    def load_json_str(cls, string: str, **loader_kwargs: Any) -> Self:
        """
        Create options from a JSON string.

        Parameters
        ----------
        string : str
            JSON representation of the options.
        **loader_kwargs : Any
            Ignored.

        Returns
        -------
        Options
            Decoded options.
        """
        return cls.loads(string)

    def get_hash(self) -> str:
        """
        Return a hash of the options.

        Private keys and the run control keys branch_prefix, commit_message, push, debug
        and force do not contribute to the hash.

        Returns
        -------
        str
            Base 32 encoded SHA-1 hash of the sorted options.
        """
        excluded_keys = {"branch_prefix", "commit_message", "push", "debug", "force"}
        remaining_dict = remove_invalid_keys(self, excluded_keys=excluded_keys)
        dump = json.dumps(
            remaining_dict,
            cls=CustomEncoder,
            ensure_ascii=False,
            sort_keys=True,
            indent=None,
            separators=(',', ':'),
        )

        hash_alphabet = "abcdefghjkmnpqrstvwxyz0123456789"
        hash_base = len(hash_alphabet)

        def to_base(number: int, base: int) -> str:
            result = ""
            while number:
                result += hash_alphabet[number % base]
                number //= base
            return result[::-1] or "0"

        base_16_hash = hashlib.sha1(dump.encode('utf-8')).hexdigest()
        base_10_hash = int(base_16_hash, 16)
        base_32_hash = to_base(base_10_hash, hash_base)

        return base_32_hash

    def __eq__(self, other: object) -> bool:
        """Compare options by their hash."""
        if not isinstance(other, Options):
            try:
                other = Options(other)
            except TypeError:
                print(f"TypeError when casting {other} to Options()")
                return NotImplemented

        return self.get_hash() == other.get_hash()


if __name__ == '__main__':
    options = Options()
    options.optimizer_options = 10
    options.commit_message = "Fuubar"
    options_rev = Options.load_json_str(options.dump_json_str())
    print(options.dump_json_str())
    options_rev.commit_message = "unfoo"
    print(options.__hash__(), options_rev.__hash__())
