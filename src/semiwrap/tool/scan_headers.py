import fnmatch
import glob
from itertools import chain
from os.path import join, relpath
from pathlib import Path


from .util import get_setup


class HeaderScanner:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "scan-headers",
            help="Generate a list of headers in TOML form",
            parents=[parent_parser],
        )
        parser.add_argument("--all", default=False, action="store_true")
        return parser

    def run(self, args):
        s = get_setup()

        to_ignore = s.project.scan_headers_ignore

        def _should_ignore(f):
            for pat in to_ignore:
                if fnmatch.fnmatch(f, pat):
                    return True
            return False

        already_present = {}
        if not args.all:
            for i, wrapper in enumerate(s.project.wrappers.values()):
                files = set()
                if wrapper.autogen_headers:
                    files |= {Path(f) for f in wrapper.autogen_headers.values()}
                if wrapper.type_casters:
                    files |= {Path(tc.header) for tc in wrapper.type_casters}
                if not files:
                    continue
                for incdir in s.wrappers[i]._generation_search_path():
                    ifiles = already_present.setdefault(incdir, set())
                    incdir = Path(incdir)
                    for f in files:
                        if (incdir / f).exists():
                            ifiles.add(f)

        for wrapper in s.wrappers:
            printed = False

            # This uses the direct include directories instead of the generation
            # search path as we only want to output a file once
            for incdir in wrapper.get_include_dirs():
                wpresent = already_present.get(incdir, set())

                files = list(
                    sorted(
                        Path(relpath(f, incdir))
                        for f in chain(
                            glob.glob(join(incdir, "**", "*.h"), recursive=True),
                            glob.glob(join(incdir, "**", "*.hpp"), recursive=True),
                        )
                        if "rpygen" not in f and not _should_ignore(relpath(f, incdir))
                    )
                )

                files = [f for f in files if f not in wpresent]
                if not files:
                    continue

                if not printed:
                    print(
                        f'[tool.robotpy-build.wrappers."{wrapper.package_name}".autogen_headers]'
                    )
                    printed = True

                lastdir = None
                for f in files:
                    thisdir = f.parent
                    if lastdir is None:
                        if thisdir:
                            print("#", thisdir)
                    elif lastdir != thisdir:
                        print()
                        if thisdir:
                            print("#", thisdir)
                    lastdir = thisdir

                    base = f.stem
                    print(f'{base} = "{f.as_posix()}"')
                print()
