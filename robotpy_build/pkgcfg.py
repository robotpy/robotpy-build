# Used by robotpybuild entry point

from os.path import abspath, join, dirname
from typing import Dict, List, Optional

_root = abspath(dirname(__file__))


def get_include_dirs() -> Optional[List[str]]:
    return [join(_root, "pybind11", "include"), join(_root, "include")]


def get_library_dirs() -> Optional[List[str]]:
    pass
