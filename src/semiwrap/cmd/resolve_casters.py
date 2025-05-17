"""
Creates a per-module data file mapping type names to header files containing
pybind11 type caster implementations.
"""

import inspect
import pathlib
import pickle
import sys

from ..casters import CastersData, load_typecaster_json_data, TypeData
from ..depfile import Depfile


def _update_all_casters(type_caster_cfg: pathlib.Path, all_casters: CastersData):
    data = load_typecaster_json_data(type_caster_cfg)

    # flatten it
    for item in data.headers:
        header = pathlib.Path(item.header)
        if header.is_absolute():
            raise ValueError(
                f"{type_caster_cfg} contains absolute path to header: {header}"
            )

        for typ in item.types:
            td = TypeData(
                header=header, typename=typ, default_arg_cast=item.default_arg_cast
            )

            if typ not in all_casters:
                all_casters[typ] = td

            # in addition to the type, add a non-namespaced version too
            # - in theory this could cause conflicts, but in practice its useful
            # - this could be solved by making the parser resolve namespaces, but
            #   that has downsides too
            ntyp = typ.split("::")[-1]
            if ntyp not in all_casters:
                all_casters[ntyp] = td


def main():
    try:
        _, outfile_arg, depfile_arg = sys.argv[:3]
        caster_json_files = sys.argv[3:]
    except ValueError:
        print(inspect.cleandoc(__doc__ or ""), file=sys.stderr)
        sys.exit(1)

    outfile = pathlib.Path(outfile_arg)
    depfile = pathlib.Path(depfile_arg)

    d = Depfile(outfile)
    content: CastersData = {}

    for f in caster_json_files:
        path = pathlib.Path(f)
        d.add(path)
        _update_all_casters(path, content)

    # write the depfile
    d.write(depfile)

    # write the pickled data
    with open(outfile, "wb") as fp:
        pickle.dump(content, fp)


if __name__ == "__main__":
    main()
