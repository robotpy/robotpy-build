import dataclasses
import json
import typing as T

from validobj.errors import ValidationError
from validobj.validation import parse_input

PKGCONF_CASTER_EXT = ".pybind11.json"


@dataclasses.dataclass
class TypeCasterHeader:
    header: str
    types: T.List[str]
    default_arg_cast: bool = False


#: content of .pybind11.json
@dataclasses.dataclass
class TypeCasterData:
    headers: T.List[TypeCasterHeader] = dataclasses.field(default_factory=list)


def load_typecaster_data(fname) -> TypeCasterData:
    with open(fname) as fp:
        try:
            return parse_input(json.load(fp), TypeCasterData)
        except ValidationError as e:
            raise ValidationError(f"Error processing {fname}")


def save_typecaster_data(fname, data: TypeCasterData):
    with open(fname, "w") as fp:
        json.dump(dataclasses.asdict(data), fp)


#: content of pickle file
CastersData = T.Dict[str, T.Dict[str, T.Any]]
