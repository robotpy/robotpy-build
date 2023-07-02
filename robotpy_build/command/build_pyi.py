from contextlib import contextmanager
import importlib.util
import json
import os
from os.path import abspath, exists, dirname, join
import subprocess
import sys

import re
from typing import Any

import pybind11_stubgen
from setuptools import Command
from distutils.errors import DistutilsError

from .util import get_install_root


class GeneratePyiError(DistutilsError):
    pass


class BuildPyi(Command):
    base_package: str

    command_name = "build_pyi"
    description = "Generates pyi files from built extensions"

    user_options = [("build-lib=", "d", 'directory to "build" (copy) to')]

    def initialize_options(self):
        self.build_lib = None

    def finalize_options(self):
        self.set_undefined_options("build", ("build_lib", "build_lib"))

    def run(self):
        # cannot build pyi files when cross-compiling
        if (
            "_PYTHON_HOST_PLATFORM" in os.environ
            or "PYTHON_CROSSENV" in os.environ
            or os.environ.get("RPYBUILD_SKIP_PYI") == "1"
        ):
            return

        # Gather information for needed stubs
        data = {"mapping": {}, "stubs": []}

        # OSX-specific: need to set DYLD_LIBRARY_PATH otherwise modules don't
        # work. Luckily, that information was computed when building the
        # extensions...
        env = os.environ.copy()
        dyld_path = set()

        # Requires information from build_ext to work
        build_ext = self.distribution.get_command_obj("build_ext")
        if build_ext.inplace:
            data["out"] = get_install_root(self)
        else:
            data["out"] = self.build_lib

        # Ensure that the associated packages can always be found locally
        for wrapper in build_ext.wrappers:
            pkgdir = wrapper.package_name.split(".")
            init_py = abspath(join(self.build_lib, *pkgdir, "__init__.py"))
            if exists(init_py):
                data["mapping"][wrapper.package_name] = init_py

        # Ensure that the built extension can always be found
        for ext in build_ext.extensions:
            fname = build_ext.get_ext_filename(ext.name)
            data["mapping"][ext.name] = abspath(join(self.build_lib, fname))
            data["stubs"].append(ext.name)

            rpybuild_libs = getattr(ext, "rpybuild_libs", None)
            if rpybuild_libs:
                for pth, _ in rpybuild_libs.values():
                    dyld_path.add(dirname(pth))

        # Don't do anything if nothing is needed
        if not data["stubs"]:
            return

        # OSX-specific
        if dyld_path:
            dyld_path = ":".join(dyld_path)
            if "DYLD_LIBRARY_PATH" in env:
                dyld_path += ":" + env["DYLD_LIBRARY_PATH"]
            env["DYLD_LIBRARY_PATH"] = dyld_path

        data_json = json.dumps(data)

        # Execute in a subprocess in case it crashes
        args = [sys.executable, "-m", __name__]
        try:
            subprocess.run(args, input=data_json.encode("utf-8"), env=env, check=True)
        except subprocess.CalledProcessError:
            raise GeneratePyiError(
                "Failed to generate .pyi file (see above, or set RPYBUILD_SKIP_PYI=1 to ignore) via %s"
                % (args,)
            ) from None

        # Create a py.typed for PEP 561
        with open(join(data["out"], *self.base_package.split("."), "py.typed"), "w"):
            pass


class _PackageFinder:
    """
    Custom loader to allow loading built modules from their location
    in the build directory (as opposed to their install location)
    """

    mapping = {}

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        m = cls.mapping.get(fullname)
        if m:
            return importlib.util.spec_from_file_location(fullname, m)


def main():
    cfg = json.load(sys.stdin)

    # Configure custom loader
    _PackageFinder.mapping = cfg["mapping"]
    sys.meta_path.insert(0, _PackageFinder)

    # Generate pyi modules
    sys.argv = [
        "<dummy>",
        "--no-setup-py",
        # "--use-numpy-nptyping", # After stubgen PR
        "--log-level=WARNING",
        "--root-module-suffix=",
        "--ignore-invalid",
        "defaultarg",
        "-o",
        cfg["out"],
    ] + cfg["stubs"]

    math_to_add = {}

    class fp_wrapper:
        def __init__(self, fp) -> None:
            self.fp = fp
        
        def write(self, s: str) -> None:
            # fix underscored names
            s = re.sub(r"([a-zA-Z0-9_]+)\._\1", r"\1", s)
            self.fp.write(s)

        def __getattr__(self, __name: str) -> Any:
            return getattr(self.fp, __name)


    @contextmanager
    def open_wrapper(file, *args, **kwargs):
        with open(file, *args, **kwargs) as fp:
            import typing
            fp: typing.TextIO
            ### before pyi write
            fp.write("#\n# AUTOMATICALLY GENERATED FILE, DO NOT EDIT!\n#\n\n")

            # yield fp ### pyi write
            yield fp_wrapper(fp) ### pyi write
            ### after pyi write

            # Add buffer definition
            if sys.version_info >= (3, 12):
                fp.write("\n\nfrom collections.abc import Buffer\n\n")
            else:
                fp.write("\n\nBuffer = typing.Union[bytes, bytearray, memoryview]\n\n")

            # Add math units
            for cpp_type, py_type in math_to_add.items():
                if sys.version_info >= (3, 12):
                    fp.write(f"\n\ntype {cpp_type} = {py_type}\n\n")
                elif sys.version_info >= (3, 10):
                    fp.write(f"\n\n{cpp_type}: typing.TypeAlias = {py_type}\n\n")
                else:
                    fp.write(f"\n\n{cpp_type} = {py_type}\n\n")
    
    # buffer
    pybind11_stubgen.StubsGenerator.GLOBAL_CLASSNAME_REPLACEMENTS[
        re.compile(r"(buffer)")
    ] = lambda _: "Buffer"

    @pybind11_stubgen.function_docstring_preprocessing_hooks.append
    def fix_unsupported_escape_sequence_in_string_literal(docstring: str) -> str:
        return docstring.replace("\\_", "_")

    def replace_sub_callback(match: re.Match):
        if match.group(1) in math_to_add and match.group(2) != math_to_add[match.group(1)]:
            print("WARNING: math unit already defined with different value:", match.group(1), "->",  match.group(2), "and", math_to_add[match.group(1)])
        math_to_add[match.group(1)] = match.group(2)
        return match.group(1)

    @pybind11_stubgen.function_docstring_preprocessing_hooks.append
    def replace_math_units(docstring: str) -> str:
        return re.sub(r"STUBGEN_CPP_(.*?)_IS_PY_(.*?)_STUBGEN", replace_sub_callback, docstring)

    pybind11_stubgen.open = open_wrapper # type: ignore
    pybind11_stubgen.main()


if __name__ == "__main__":
    main()
