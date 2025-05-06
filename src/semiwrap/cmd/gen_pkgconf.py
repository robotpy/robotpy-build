"""
Generates a pkg-config file for this extension
"""

import argparse
import inspect
import pathlib

from ..mkpc import make_pc_file
from ..pyproject import PyProject


def main():
    parser = argparse.ArgumentParser(usage=inspect.cleandoc(__doc__ or ""))
    parser.add_argument("module_package_name")
    parser.add_argument("name")
    parser.add_argument("pyproject_toml", type=pathlib.Path)
    parser.add_argument("pcfile", type=pathlib.Path)
    parser.add_argument("--libinit-py")
    args = parser.parse_args()

    module_package_name = args.module_package_name
    project = PyProject(args.pyproject_toml)

    module = project.get_extension(module_package_name)
    depends = project.get_extension_deps(module)

    pc_install_path = project.package_root / pathlib.Path(
        *module_package_name.split(".")[:-1]
    )
    make_pc_file(
        project_root=project.root,
        pcfile=args.pcfile,
        pc_install_path=pc_install_path,
        name=args.name,
        desc="semiwrap pybind11 module",
        version="",
        includes=module.includes,
        depends=depends,
        libinit_py=args.libinit_py,
        generator_name="semiwrap.cmd_gen_pkgconf",
    )


if __name__ == "__main__":
    main()
