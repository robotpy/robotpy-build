import argparse
import glob
import inspect
from os.path import basename, dirname, exists, join, relpath, splitext
from pathlib import PurePosixPath
import pprint
import subprocess
import sys

from .setup import Setup
from .generator_data import MissingReporter
from .command.util import get_build_temp_path

from . import platforms


def get_setup() -> Setup:
    s = Setup()
    s.prepare()

    temp_path = join(get_build_temp_path(), "dlstatic")
    for static_lib in s.static_libs:
        static_lib.set_root(temp_path)

    return s


class BuildDep:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "build-dep", help="Install build dependencies", parents=[parent_parser]
        )
        parser.add_argument("--install", help="Actually do it", action="store_true")
        parser.add_argument("--find-links", help="Find links arg", default=None)
        return parser

    def run(self, args):
        s = get_setup()
        requirements = s.pyproject.get("build-system", {}).get("requires", [])
        requirements.extend(s.setup_kwargs.get("install_requires", ""))
        requirements.append("wheel")

        pipargs = [
            sys.executable,
            "-m",
            "pip",
            "--disable-pip-version-check",
            "install",
        ]
        if args.find_links:
            pipargs.extend(
                ["--find-links", args.find_links,]
            )

        pipargs.extend(requirements)
        print(" ".join(pipargs))

        if args.install:
            p = subprocess.run(pipargs)
            return p.returncode


class GenCreator:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "create-gen",
            help="Create YAML files from parsed header files",
            parents=[parent_parser],
        )
        parser.add_argument(
            "--write", help="Write to files if they don't exist", action="store_true"
        )
        parser.add_argument("--strip-prefixes", action="append")

        return parser

    def run(self, args):

        pfx = ""
        if args.strip_prefixes:
            pfx = "strip_prefixes:\n- " + "\n- ".join(args.strip_prefixes) + "\n\n"

        s = get_setup()
        for wrapper in s.wrappers:
            reporter = MissingReporter()
            wrapper.on_build_gen("", reporter)

            nada = True
            for name, report in reporter.as_yaml():
                report = f"---\n\n{pfx}{report}"

                nada = False
                if args.write:
                    if not exists(name):
                        print("Writing", name)
                        with open(name, "w") as fp:
                            fp.write(report)
                    else:
                        print(name, "already exists!")

                print("===", name, "===")
                print(report)

            if nada:
                print("Nothing to do!")


class HeaderScanner:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "scan-headers",
            help="Generate a list of headers in TOML form",
            parents=[parent_parser],
        )
        return parser

    def run(self, args):
        s = get_setup()
        for wrapper in s.wrappers:
            for incdir in wrapper.get_include_dirs():
                files = list(
                    sorted(
                        relpath(f, incdir)
                        for f in glob.glob(join(incdir, "**", "*.h"), recursive=True)
                    )
                )

                print("generate = [")
                lastdir = None
                for f in files:
                    if "rpygen" not in f:
                        thisdir = dirname(f)
                        if lastdir is None:
                            if thisdir:
                                print("    #", PurePosixPath(thisdir))
                        elif lastdir != thisdir:
                            print()
                            if thisdir:
                                print("    #", PurePosixPath(thisdir))
                        lastdir = thisdir

                        base = splitext(basename(f))[0]
                        f = PurePosixPath(f)
                        print(f'    {{ {base} = "{f}" }},')
                print("]")


class ImportCreator:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "create-imports",
            help="Generate suitable imports for a module",
            parents=[parent_parser],
        )
        parser.add_argument("base", help="Ex: wpiutil")
        parser.add_argument("compiled", help="Ex: wpiutil._impl.wpiutil")
        return parser

    def run(self, args):
        # Runtime Dependency Check
        try:
            import black
        except:
            print("Error, The following module is required to run this tool: black")
            exit(1)

        # TODO: could probably generate this from parsed code, but seems hard
        ctx = {}
        exec(f"from {args.compiled} import *", {}, ctx)

        relimport = "." + ".".join(
            args.compiled.split(".")[len(args.base.split(".")) :]
        )

        stmt = inspect.cleandoc(
            f"""

            # autogenerated by 'robotpy-build create-imports {args.base} {args.compiled}'
            from {relimport} import {','.join(sorted(ctx.keys()))}
            __all__ = ["{'", "'.join(sorted(ctx.keys()))}"]
        
        """
        )

        print(
            subprocess.check_output(
                ["black", "-", "-q"], input=stmt.encode("utf-8")
            ).decode("utf-8")
        )


class LibraryRelinker:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "relink-libraries",
            help="Relink libraries to new paths",
            parents=[parent_parser],
        )
        parser.add_argument("libraries", help="Folder with libraries - Ex: ./libs")
        parser.add_argument(
            "dependents",
            help="Folder with dependents - Ex: ../../venv/libs/site-packages",
        )
        return parser

    def run(self, args):
        raise NotImplementedError(
            "tool needs to be fixed -- just reinstall the offending package instead"
        )
        # Essentially a macos check
        try:
            import delocate
        except:
            print("relink-libraries is only designed to work on macOS.")
            print("If you are on macOS, then:")
            print("Error, The following module is required to run this tool: delocate")
            exit(1)

        from . import relink_libs
        from os.path import abspath

        dependencies = relink_libs.get_build_dependencies(args.dependents)
        libs = relink_libs.find_all_libs(args.libraries)
        for key in libs:
            libs[key] = "@" + abspath(libs[key]) + "@"

        print("Format | dependent : old path to lib -> new path to lib")
        # We are only using abs paths so build_path doesn't matter
        relink_libs.redirect_links(
            ".", libs, dependencies, auto_detect=False, supress_errors=True
        )


class PlatformInfo:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "platform-info",
            help="Displays platform-specific information",
            parents=[parent_parser],
        )
        return parser

    def run(self, args):
        p = platforms.get_platform()
        print("platform:")
        pprint.pprint(p)
        print()

        print("override keys:")
        pprint.pprint(platforms.get_platform_override_keys(p))


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
        LibraryRelinker,
        PlatformInfo,
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

    exit(retval)
