import os.path
import pathlib
import typing as T


def maybe_write_file(
    path: pathlib.Path, content: str, *, encoding: T.Optional[str] = None
) -> bool:
    # returns True if new content written
    if path.exists():
        with open(path, encoding=encoding) as fp:
            oldcontent = fp.read()
        if oldcontent == content:
            return False
    elif not path.parent.exists():
        path.parent.mkdir(parents=True)

    with open(path, "w", encoding=encoding) as fp:
        fp.write(content)

    return True


def relpath_walk_up(p: pathlib.Path, other: pathlib.Path) -> pathlib.Path:
    # walk_up=True was introduced in Python 3.12 so can't use that
    #   p.relative_to(other, walk_up=True)
    return pathlib.Path(os.path.relpath(p, other))
