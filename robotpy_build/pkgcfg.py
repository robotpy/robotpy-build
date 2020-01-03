# Used by robotpybuild entry point

from os.path import abspath, join, dirname
from typing import Dict, List, Optional

_root = abspath(dirname(__file__))


def get_include_dirs() -> Optional[List[str]]:
    return [join(_root, "pybind11", "include"), join(_root, "include")]


def get_library_dirs() -> Optional[List[str]]:
    pass


def get_type_casters(casters: Dict[str, str]) -> None:
    casters.update(
        {
            "std::vector": "pybind11/stl.h",
            "std::deque": "pybind11/stl.h",
            "std::list": "pybind11/stl.h",
            "std::array": "pybind11/stl.h",
            "std::valarray": "pybind11/stl.h",
            "std::set": "pybind11/stl.h",
            "std::map": "pybind11/stl.h",
            "std::unordered_map": "pybind11/stl.h",
            "std::optional": "pybind11/stl.h",
            "std::nullopt_t": "pybind11/stl.h",
            "std::variant": "pybind11/stl.h",
            "std::function": "pybind11/functional.h",
            "std::complex": "pybind11/complex.h",
            "std::chrono::duration": "pybind11/chrono.h",
            "std::chrono::time_point": "pybind11/chrono.h",
        }
    )
