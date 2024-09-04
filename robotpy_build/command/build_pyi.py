import json
import os
from os.path import exists, dirname, join
import subprocess
import sys

import pybind11_stubgen

try:
    from setuptools.errors import BaseError
except ImportError:
    from distutils.errors import DistutilsError as BaseError

from ._built_env import _BuiltEnv, _PackageFinder


class GeneratePyiError(BaseError):
    pass


class BuildPyi(_BuiltEnv):
    base_package: str

    command_name = "build_pyi"
    description = "Generates pyi files from built extensions"

    def run(self):
        # cannot build pyi files when cross-compiling
        if (
            "_PYTHON_HOST_PLATFORM" in os.environ
            or "PYTHON_CROSSENV" in os.environ
            or os.environ.get("RPYBUILD_SKIP_PYI") == "1"
        ):
            return

        # Gather information for needed stubs
        data, env = self.setup_built_env()
        data["stubs"] = []

        # Ensure that the built extension can always be found
        build_ext = self.get_finalized_command("build_ext")
        for ext in build_ext.extensions:
            data["stubs"].append(ext.name)

        # Don't do anything if nothing is needed
        if not data["stubs"]:
            return

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


def main():
    cfg = json.load(sys.stdin)

    # Configure custom loader
    _PackageFinder.mapping = cfg["mapping"]
    sys.meta_path.insert(0, _PackageFinder)

    # Generate pyi modules
    out = cfg["out"]
    for stub in cfg["stubs"]:
        sys.argv = [
            "<dummy>",
            "--exit-code",
            "--ignore-invalid-expressions=<.*>",
            "--root-suffix=",
            "-o",
            out,
            stub,
        ]

        pybind11_stubgen.main()


if __name__ == "__main__":
    main()
