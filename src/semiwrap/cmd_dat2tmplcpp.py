"""
Creates an output .hpp file from a .dat file created by parsing a header
"""

import inspect
import pathlib
import pickle
import sys

from .autowrap.context import HeaderContext
from .autowrap.render_cls_rpy_include import render_cls_rpy_include_hpp
from .util import maybe_write_file


def _write_wrapper_cpp(
    input_dat: pathlib.Path, class_name: str, output_hpp: pathlib.Path
):
    with open(input_dat, "rb") as fp:
        hctx = pickle.load(fp)

    assert isinstance(hctx, HeaderContext)

    for cls in hctx.classes:
        if cls.full_cpp_name == class_name:
            break
    else:
        raise ValueError(f"internal error: cannot find {class_name}")

    content = render_cls_rpy_include_hpp(hctx, cls)
    maybe_write_file(output_hpp, content)


def main():
    try:
        _, input_dat, class_name, output_hpp = sys.argv
    except ValueError:
        print(inspect.cleandoc(__doc__ or ""), file=sys.stderr)
        sys.exit(1)

    _write_wrapper_cpp(pathlib.Path(input_dat), class_name, pathlib.Path(output_hpp))


if __name__ == "__main__":
    main()
