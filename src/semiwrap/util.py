import pathlib


def maybe_write_file(path: pathlib.Path, content: str) -> bool:
    # returns True if new content written
    if path.exists():
        with open(path) as fp:
            oldcontent = fp.read()
        if oldcontent == content:
            return False
    elif not path.parent.exists():
        path.parent.mkdir(parents=True)

    with open(path, "w") as fp:
        fp.write(content)

    return True
