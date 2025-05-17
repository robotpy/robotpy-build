"""
Creates an output .hpp file from a .dat file created by parsing a header
"""

import inspect
import pathlib
import pickle
import sys

from ..autowrap.context import HeaderContext, ClassContext
from ..autowrap.render_cls_trampoline_hpp import render_cls_trampoline_hpp


def _get_classes(hctx: HeaderContext):
    def _get_child_classes(c: ClassContext):
        for c in c.child_classes:
            yield c
            _get_child_classes(c)

    for cls in hctx.classes:
        yield cls
        yield from _get_child_classes(cls)


def _write_wrapper_cpp(input_dat: pathlib.Path, yml_id: str, output_hpp: pathlib.Path):
    with open(input_dat, "rb") as fp:
        hctx = pickle.load(fp)

    assert isinstance(hctx, HeaderContext)

    avail = []
    for cls in _get_classes(hctx):
        avail.append(cls.yml_id)
        if cls.yml_id == yml_id:
            break
    else:
        msg = [
            f"cannot find {yml_id} in {hctx.rel_fname}",
            f"- config: {hctx.orig_yaml}",
        ]

        if avail:
            msg.append("- found " + ", ".join(avail))

        if hctx.ignored_classes:
            msg.append("- ignored " + ", ".join(hctx.ignored_classes))

        raise ValueError("\n".join(msg))

    content = render_cls_trampoline_hpp(hctx, cls)
    output_hpp.write_text(content, encoding="utf-8")


def main():
    try:
        _, input_dat, yml_id, output_hpp = sys.argv
    except ValueError:
        print(inspect.cleandoc(__doc__ or ""), file=sys.stderr)
        sys.exit(1)

    _write_wrapper_cpp(pathlib.Path(input_dat), yml_id, pathlib.Path(output_hpp))


if __name__ == "__main__":
    main()
