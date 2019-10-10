# Used by robotpybuild entry point

from os.path import abspath, dirname, join


def get_include_dirs():
    return [abspath(join(dirname(__file__), "pybind11", "include"))]


def get_library_dirs():
    pass
