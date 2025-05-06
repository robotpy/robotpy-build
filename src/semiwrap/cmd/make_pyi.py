"""
Creates an output .pyi file from a given python module.

Arguments are:
    package outpath [subpackage outpath...] -- package mapped_file
"""

import importlib.util
import inspect
import os
from os.path import dirname, join
import pathlib
import shutil
import sys
import tempfile
import typing as T

import pybind11_stubgen


class _PackageFinder:
    """
    Custom loader to allow loading built modules from their location
    in the build directory (as opposed to their install location)
    """

    # Set this to mapping returned from _BuiltEnv.setup_built_env
    mapping: T.Dict[str, str] = {}

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        m = cls.mapping.get(fullname)
        if m:
            return importlib.util.spec_from_file_location(fullname, m)


def _write_pyi(
    package_name, generated_pyi: T.Dict[pathlib.PurePosixPath, pathlib.Path]
):

    # We can't control where stubgen writes files, so tell it to output
    # to a temporary directory and then we copy the files from there to
    # our desired location
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_pth = pathlib.Path(tmpdir)

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

        # Create the parent directories in the temporary directory
        for infile in generated_pyi.keys():
            (tmpdir_pth / infile).parent.mkdir(parents=True, exist_ok=True)

        pybind11_stubgen.main()

        # stubgen doesn't take a direct output filename, so move the file
        # to our desired location
        for infile, output in generated_pyi.items():
            output.unlink(missing_ok=True)
            shutil.move(tmpdir_pth / infile, output)


def main():

    generated_pyi: T.Dict[pathlib.PurePosixPath, pathlib.Path] = {}
    argv = sys.argv

    if len(argv) < 3:
        print(inspect.cleandoc(__doc__ or ""), file=sys.stderr)
        sys.exit(1)

    # Package name first
    package_name = argv[1]

    # Output file map: input output
    idx = 2
    while idx < len(argv):
        if argv[idx] == "--":
            idx += 1
            break

        generated_pyi[pathlib.PurePosixPath(argv[idx])] = pathlib.Path(argv[idx + 1])
        idx += 2

    # Arguments are used to set up the package map
    package_map = _PackageFinder.mapping
    for i in range(idx, len(argv), 2):
        # python 3.9 requires paths to be resolved
        package_map[argv[i]] = os.fspath(pathlib.Path(argv[i + 1]).resolve())

    # Add parent packages too
    # .. assuming there are __init__.py in each package
    for pkg in list(package_map.keys()):
        while True:
            idx = pkg.rfind(".")
            if idx == -1:
                break
            ppkg = pkg[:idx]
            if ppkg not in package_map:
                package_map[ppkg] = join(
                    dirname(dirname(package_map[pkg])), "__init__.py"
                )
            pkg = ppkg

    sys.meta_path.insert(0, _PackageFinder)

    _write_pyi(package_name, generated_pyi)


if __name__ == "__main__":
    main()
