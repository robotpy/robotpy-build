import argparse
import sys

from .build_dep import BuildDep
from .create_gen import GenCreator
from .create_imports import ImportCreator
from .parse_maven import MavenParser
from .platform_info import PlatformInfo
from .show_override import ShowOverrides
from .scan_headers import HeaderScanner


def main():
    parser = argparse.ArgumentParser(prog="robotpy-build")
    parent_parser = argparse.ArgumentParser(add_help=False)
    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True

    for cls in (
        BuildDep,
        GenCreator,
        HeaderScanner,
        ImportCreator,
        PlatformInfo,
        ShowOverrides,
        MavenParser,
    ):
        cls.add_subparser(parent_parser, subparsers).set_defaults(cls=cls)

    args = parser.parse_args()
    cmd = args.cls()
    retval = cmd.run(args)

    if retval is False:
        retval = 1
    elif retval is True:
        retval = 0
    elif isinstance(retval, int):
        pass
    else:
        retval = 0

    return retval


if __name__ == "__main__":
    sys.exit(main())
