import dataclasses
import os
import pathlib
import typing as T


def _escape_dep(dep: str):
    dep = dep.replace("\\", "\\\\")
    dep = dep.replace(" ", "\\ ")
    return dep


@dataclasses.dataclass
class Depfile:
    # TODO: currently only supports single output target

    target: pathlib.Path
    deps: T.List[pathlib.Path] = dataclasses.field(default_factory=list)

    def add(self, dep: pathlib.Path):
        self.deps.append(dep)

    def write(self, path: pathlib.Path):
        """
        Write make-compatible depfile
        """
        with open(path, "w") as fp:
            target = _escape_dep(str(self.target.absolute()))
            fp.write(f"{target}:")
            for dep in self.deps:
                fp.write(f" \\\n  {_escape_dep(str(dep.absolute()))}")
            fp.write("\n")
