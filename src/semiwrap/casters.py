import dataclasses
import json
import pathlib
import typing as T

from .config.util import parse_input

PKGCONF_CASTER_EXT = ".pybind11.json"

#
# JSON caster data
#


@dataclasses.dataclass
class TypeCasterJsonHeader:
    header: str
    types: T.List[str]
    default_arg_cast: bool = False


#: content of .pybind11.json
@dataclasses.dataclass
class TypeCasterJsonData:
    """
    Stored in *.pybind11.json
    """

    headers: T.List[TypeCasterJsonHeader] = dataclasses.field(default_factory=list)


def load_typecaster_json_data(fname) -> TypeCasterJsonData:
    with open(fname, encoding="utf-8") as fp:
        return parse_input(json.load(fp), TypeCasterJsonData, fname)


def save_typecaster_json_data(fname: pathlib.Path, data: TypeCasterJsonData):
    with open(fname, "w", encoding="utf-8") as fp:
        json.dump(dataclasses.asdict(data), fp)


#
# Pickled caster lookup as stored by resolve_casters
#


@dataclasses.dataclass
class TypeData:
    header: pathlib.Path
    typename: str
    default_arg_cast: bool


#: content of pickle file used internally
CastersData = T.Dict[str, TypeData]
