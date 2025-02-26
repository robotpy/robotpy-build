"""
Creates an output .pyi file from a given python module
"""

import importlib.util
import inspect
import pathlib
import sys
import tempfile

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

    with tempfile.TemporaryDirectory() as tmpdir:
        # Call pybind11-stubgen
        sys.argv = [
            "<dummy>",
            "--exit-code",
            "--ignore-invalid-expressions=<.*>",
            "--root-suffix=",
            "-o",
            tmpdir,
            package_name,
        ]

        pybind11_stubgen.main()

        # stubgen doesn't take a direct output filename, so move the file
        # to our desired location
        elems = package_name.split(".")
        elems[-1] = f"{elems[-1]}.pyi"
        pathlib.Path(tmpdir, *elems).rename(output_pyi)


def main():
    try:
        _, package_name, output_pyi = sys.argv[:3]
    except ValueError:
        print(inspect.cleandoc(__doc__ or ""), file=sys.stderr)
        sys.exit(1)

    # Arguments are used to set up the package map
    for i in range(3, len(sys.argv), 2):
        _PackageFinder.mapping[sys.argv[i]] = sys.argv[i + 1]

    sys.meta_path.insert(0, _PackageFinder)

    _write_pyi(package_name, output_pyi)


if __name__ == "__main__":
    main()
