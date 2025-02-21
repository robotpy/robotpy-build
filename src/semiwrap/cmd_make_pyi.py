"""
Creates an output .pyi file from a given python module
"""

import importlib.util
import inspect
import sys

import pybind11_stubgen


class _PackageFinder:
    """
    Custom loader to allow loading built modules from their location
    in the build directory (as opposed to their install location)
    """

    # Set this to mapping returned from _BuiltEnv.setup_built_env
    mapping = {}

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        m = cls.mapping.get(fullname)
        if m:
            return importlib.util.spec_from_file_location(fullname, m)


def _write_pyi(package_name: str, output_pyi: str):
    # Need to:
    # - add the original source directory to python path
    # - add the built extensions to the mapping
    # - other related nonsense
    # ... maybe this could be a meson dist script?

    # Configure custom loader
    # _PackageFinder.mapping = cfg["mapping"]
    # sys.meta_path.insert(0, _PackageFinder)

    # # Call pybind11-stubgen
    # sys.argv = [
    #     "<dummy>",
    #     "--exit-code",
    #     "--ignore-invalid-expressions=<.*>",
    #     "--root-suffix=",
    #     "-o",
    #     output_pyi,
    #     package_name,
    # ]

    # pybind11_stubgen.main()
    with open(output_pyi, "w") as fp:
        fp.write("# TODO\n")


def main():
    try:
        _, package_name, output_pyi = sys.argv
    except ValueError:
        print(inspect.cleandoc(__doc__ or ""), file=sys.stderr)
        sys.exit(1)

    _write_pyi(package_name, output_pyi)


if __name__ == "__main__":
    main()
