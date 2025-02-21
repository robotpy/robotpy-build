"""
Creates an output .cpp file from a .dat file created by parsing a header
"""

import inspect
import pathlib
import pickle
import sys

from .autowrap.context import HeaderContext
from .autowrap.render_wrapped import render_wrapped_cpp
from .util import maybe_write_file


def _write_wrapper_cpp(input_dat: pathlib.Path, output_cpp: pathlib.Path):
    with open(input_dat, "rb") as fp:
        hctx = pickle.load(fp)

    assert isinstance(hctx, HeaderContext)

    content = render_wrapped_cpp(hctx)
    maybe_write_file(output_cpp, content)


def main():
    try:
        _, input_dat, output_cpp = sys.argv
    except ValueError:
        print(inspect.cleandoc(__doc__ or ""), file=sys.stderr)
        sys.exit(1)

    _write_wrapper_cpp(pathlib.Path(input_dat), pathlib.Path(output_cpp))


if __name__ == "__main__":
    main()
