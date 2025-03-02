import json
import os
import subprocess
import sys
import typing

try:
    from setuptools.errors import BaseError
except ImportError:
    from distutils.errors import DistutilsError as BaseError

from ._built_env import _BuiltEnv, _PackageFinder


class UpdateInitError(BaseError):
    pass


class UpdateInit(_BuiltEnv):
    update_list: typing.List[str]

    command_name = "update_init"
    description = (
        "Updates __init__.py files using settings from tool.robotpy-build.update_init"
    )

    def run(self):
        # cannot use when cross-compiling
        if (
            "_PYTHON_HOST_PLATFORM" in os.environ
            or "PYTHON_CROSSENV" in os.environ
            or not self.update_list
        ):
            return

        data, env = self.setup_built_env()
        data["update_list"] = self.update_list

        data_json = json.dumps(data)

        # Execute in a subprocess in case it crashes
        args = [sys.executable, "-m", __name__]
        try:
            subprocess.run(args, input=data_json.encode("utf-8"), env=env, check=True)
        except subprocess.CalledProcessError:
            raise UpdateInitError(
                "Failed to generate .pyi file (see above, or set RPYBUILD_SKIP_PYI=1 to ignore) via %s"
                % (args,)
            ) from None


def main():
    cfg = json.load(sys.stdin)

    # Configure custom loader
    _PackageFinder.mapping = cfg["mapping"]
    sys.meta_path.insert(0, _PackageFinder)

    from .. import tool

    # Update init

    for to_update in cfg["update_list"]:

        sys.argv = ["<dummy>", "create-imports", "-w"] + to_update.split(" ", 1)

        retval = tool.main()
        if retval != 0:
            break


if __name__ == "__main__":
    main()
