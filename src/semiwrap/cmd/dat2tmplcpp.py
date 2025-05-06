"""
Creates a template instance .cpp file from a .dat file created by parsing a header
"""

import inspect
import pathlib
import pickle
import sys

from ..autowrap.context import HeaderContext
from ..autowrap.render_tmpl_inst import render_template_inst_cpp


def _write_wrapper_cpp(input_dat: pathlib.Path, py_name: str, output_cpp: pathlib.Path):
    with open(input_dat, "rb") as fp:
        hctx = pickle.load(fp)

    assert isinstance(hctx, HeaderContext)

    for tmpl in hctx.template_instances:
        if tmpl.py_name == py_name:
            break
    else:
        raise ValueError(f"internal error: cannot find {py_name} in {hctx.orig_yaml}")

    content = render_template_inst_cpp(hctx, tmpl)
    output_cpp.write_text(content, encoding="utf-8")


def main():
    try:
        _, input_dat, py_name, output_cpp = sys.argv
    except ValueError:
        print(inspect.cleandoc(__doc__ or ""), file=sys.stderr)
        sys.exit(1)

    _write_wrapper_cpp(pathlib.Path(input_dat), py_name, pathlib.Path(output_cpp))


if __name__ == "__main__":
    main()
