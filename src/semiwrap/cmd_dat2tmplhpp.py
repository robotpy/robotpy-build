""" """

import inspect
import pathlib
import pickle
import sys

from .autowrap.context import HeaderContext
from .autowrap.render_tmpl_inst import render_template_inst_hpp
from .util import maybe_write_file


def _write_tmpl_hpp(input_dat: pathlib.Path, output_hpp: pathlib.Path):
    with open(input_dat, "rb") as fp:
        hctx = pickle.load(fp)

    assert isinstance(hctx, HeaderContext)

    content = render_template_inst_hpp(hctx)
    maybe_write_file(output_hpp, content)


def main():
    try:
        _, input_dat, output_hpp = sys.argv
    except ValueError:
        print(inspect.cleandoc(__doc__ or ""), file=sys.stderr)
        sys.exit(1)

    _write_tmpl_hpp(pathlib.Path(input_dat), pathlib.Path(output_hpp))


if __name__ == "__main__":
    main()
