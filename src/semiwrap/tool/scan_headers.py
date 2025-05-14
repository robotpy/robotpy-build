import fnmatch
import glob
from itertools import chain
from os.path import join, relpath
from pathlib import Path, PurePosixPath
import typing as T

from ..pkgconf_cache import PkgconfCache
from ..pyproject import PyProject


class HeaderScanner:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "scan-headers",
            help="Generate a list of headers in TOML form",
            parents=[parent_parser],
        )
        parser.add_argument("--all", default=False, action="store_true")
        parser.add_argument(
            "--as-ignore",
            default=False,
            action="store_true",
            help="Emit scan_headers_ignore instead",
        )
        return parser

    def _make_search_paths(self, pyproject: PyProject) -> T.Dict[str, T.List[Path]]:
        # This logic is copied from makepath, probably should put it somewhere
        # reusable instead?

        # extension: paths
        cache = PkgconfCache()
        search_paths: T.Dict[str, T.List[Path]] = {}

        for name, cfg in pyproject.project.extension_modules.items():
            paths: T.Dict[Path, bool] = {}

            for dep in cfg.wraps:
                entry = cache.get(dep)
                for incpath in entry.include_path:
                    paths[incpath] = True

            for inc in cfg.includes:
                paths[pyproject.root / PurePosixPath(inc)] = True

            path_elems = name.split(".")
            package_path = Path(*path_elems[:-1])

            paths[pyproject.package_root / package_path] = True

            search_paths[name] = list(paths.keys())

        return search_paths

    def run(self, args):
        pyproject = PyProject()
        project = pyproject.project

        # Get the search path for each extension module
        search_paths = self._make_search_paths(pyproject)

        to_ignore = ["*/trampolines/*", "trampolines/*"] + project.scan_headers_ignore

        def _should_ignore(f):
            for pat in to_ignore:
                if fnmatch.fnmatch(f, pat):
                    return True
            return False

        all_present = set()

        if not args.all:
            for ccfg in project.export_type_casters.values():
                incs = [pyproject.root / inc for inc in ccfg.includedir]
                for h in ccfg.headers:
                    for inc in incs:
                        if (inc / h.header).exists():
                            all_present.add(inc / h.header)

            for name, ext in project.extension_modules.items():
                files = []
                for _, f in ext.headers.items():
                    if isinstance(f, str):
                        files.append(Path(f))
                    else:
                        files.append(Path(f.header))

                if not files:
                    continue
                for incdir in search_paths[name]:
                    incdir = Path(incdir)
                    for f in files:
                        if (incdir / f).exists():
                            all_present.add(incdir / f)

        all_search_paths = set()
        for ps in search_paths.values():
            for p in ps:
                all_search_paths.add(p)

        for incdir in sorted(all_search_paths, key=lambda pth: -len(pth.parts)):
            files: T.List[Path] = []

            for f in chain(
                glob.glob(join(incdir, "**", "*.h"), recursive=True),
                glob.glob(join(incdir, "**", "*.hpp"), recursive=True),
            ):
                rf = relpath(f, incdir)

                if _should_ignore(rf):
                    all_present.add(incdir / rf)
                    continue

                if (incdir / rf) in all_present:
                    continue

                files.append(Path(rf))

            if not files:
                continue

            files.sort()

            if args.as_ignore:
                comment = "    #"
            else:
                comment = "#"

            lastdir = None
            for f in files:
                thisdir = f.parent
                if lastdir is None:
                    if thisdir:
                        print(comment, thisdir)
                elif lastdir != thisdir:
                    print()
                    if thisdir:
                        print(comment, thisdir)
                lastdir = thisdir

                base = f.stem
                if args.as_ignore:
                    print(f'    "{f.as_posix()}",')
                else:
                    print(f'{base} = "{f.as_posix()}"')
            print()
