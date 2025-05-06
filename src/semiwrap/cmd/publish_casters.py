"""
Determines which casters are in the pyproject.toml and publishes them so they
can be consumed and used by other wheels.

Generates a FOO.pc file and a FOO.pybind11.json file
"""

import pathlib
import sys

from ..casters import (
    TypeCasterJsonData,
    TypeCasterJsonHeader,
    save_typecaster_json_data,
)
from ..mkpc import make_pc_file
from ..pyproject import PyProject


def main():
    try:
        _, pyproject_toml, caster_name, output_json, output_pc = sys.argv
    except ValueError:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    project = PyProject(pathlib.Path(pyproject_toml))
    cfg = project.project.export_type_casters[caster_name]

    # make sure the include directories actually exist
    include_dirs = []
    for inc in cfg.includedir:
        includedir = project.root / pathlib.Path(inc)
        include_dirs.append(includedir)
        if not includedir.exists():
            print(f"ERROR: {includedir} does not exist", file=sys.stderr)
            print(
                f"- specified at [tool.semiwrap.export_type_casters.{caster_name}].includedir",
                file=sys.stderr,
            )
            sys.exit(1)

    pc_install_path = project.package_root / pathlib.Path(*cfg.pypackage.split("."))
    make_pc_file(
        project_root=project.root,
        pcfile=pathlib.Path(output_pc),
        pc_install_path=pc_install_path,
        name=caster_name,
        desc="pybind11 type casters",
        version="",
        includes=cfg.includedir,
        depends=cfg.requires,
        libinit_py=None,
        generator_name="semiwrap.cmd_publish_casters",
    )

    #
    # Gather the data and write it next to the pc file
    #

    data = TypeCasterJsonData()
    for hdr in cfg.headers:

        # Ensure the published header actually exists
        searched = []
        for inc in include_dirs:
            full_hdr = inc / hdr.header
            if full_hdr.exists():
                break

            searched.append(full_hdr)
        else:

            print(f"ERROR: {hdr.header} does not exist", file=sys.stderr)
            print(
                f"- specified at [[tool.semiwrap.export_type_casters.{caster_name}.headers]].header",
                file=sys.stderr,
            )
            for s in searched:
                print(f"- searched '{s}'")
            sys.exit(1)

        data.headers.append(
            TypeCasterJsonHeader(
                header=hdr.header,
                types=hdr.types,
                default_arg_cast=hdr.default_arg_cast,
            )
        )

    save_typecaster_json_data(pathlib.Path(output_json), data)


if __name__ == "__main__":
    main()
