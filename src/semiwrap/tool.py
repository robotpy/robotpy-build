import argparse
import fnmatch
import glob
import inspect
from itertools import chain
from os.path import basename, dirname, exists, join, relpath
from pathlib import Path, PurePosixPath
import posixpath
import pprint
import subprocess
import sys
import types
import typing
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from collections import defaultdict
import tomli
import tomli_w
from contextlib import suppress

from .setup import Setup
from .autowrap.generator_data import MissingReporter
from .command.util import get_build_temp_path

from . import overrides
from . import platforms


def get_setup() -> Setup:
    s = Setup()
    s.prepare()
    return s


class BuildDep:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "build-dep", help="Install build dependencies", parents=[parent_parser]
        )
        parser.add_argument("--install", help="Actually do it", action="store_true")
        parser.add_argument(
            "--pre",
            action="store_true",
            default=False,
            help="Include pre-release and development versions.",
        )
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
        if args.pre:
            pipargs.append("--pre")
        if args.find_links:
            pipargs.extend(
                [
                    "--find-links",
                    args.find_links,
                ]
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


class ImportCreator:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "create-imports",
            help="Generate suitable imports for a module",
            parents=[parent_parser],
        )
        parser.add_argument("base", help="Ex: wpiutil")
        parser.add_argument("compiled", nargs="?", help="Ex: wpiutil._impl.wpiutil")
        parser.add_argument(
            "--write", "-w", action="store_true", help="Modify existing __init__.py"
        )
        return parser

    def _rel(self, base: str, compiled: str) -> str:
        base = posixpath.join(*base.split("."))
        compiled = posixpath.join(*compiled.split("."))
        elems = posixpath.relpath(compiled, base).split("/")
        elems = ["" if e == ".." else e for e in elems]
        return f".{'.'.join(elems)}"

    def run(self, args):
        self.create(args.base, args.compiled, args.write)

    def create(self, base: str, compiled: typing.Optional[str], write: bool):
        # Runtime Dependency Check
        try:
            import black
        except:
            print("Error, The following module is required to run this tool: black")
            exit(1)

        if not compiled:
            compiled = f"{base}._{base.split('.')[-1]}"

        # TODO: could probably generate this from parsed code, but seems hard
        ctx = {}
        exec(f"from {compiled} import *", {}, ctx)
        for k in list(ctx.keys()):
            if isinstance(ctx[k], types.ModuleType):
                del ctx[k]

        relimport = self._rel(base, compiled)

        stmt_compiled = "" if not compiled else f" {compiled}"
        begin_stmt = f"# autogenerated by 'robotpy-build create-imports {base}"

        stmt = inspect.cleandoc(
            f"""

            {begin_stmt}{stmt_compiled}'
            from {relimport} import {','.join(sorted(ctx.keys()))}
            __all__ = ["{'", "'.join(sorted(ctx.keys()))}"]
        
        """
        )

        content = subprocess.check_output(
            ["black", "-", "-q"], input=stmt.encode("utf-8")
        ).decode("utf-8")

        if write:
            fctx = {}
            exec(f"from {base} import __file__", {}, fctx)
            fname = fctx["__file__"]

            with open(fname) as fp:
                fcontent = orig_content = fp.read()

            # Find the beginning statement
            idx = startidx = fcontent.find(begin_stmt)
            if startidx != -1:
                for to_find in ("from", "__all__", "[", "]", "\n"):
                    idx = fcontent.find(to_find, idx)
                    if idx == -1:
                        startidx = -1
                        break

            if startidx == -1:
                # If not present, just append and let the user figure it out
                fcontent = fcontent + "\n" + content
            else:
                fcontent = fcontent[:startidx] + content + fcontent[idx + 1 :]

            if fcontent != orig_content:
                with open(fname, "w") as fp:
                    fp.write(fcontent)
                print("MOD", base)
            else:
                print("OK", base)

        else:
            print(content)


class PlatformInfo:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "platform-info",
            help="Displays platform-specific information",
            parents=[parent_parser],
        )
        parser.add_argument("--list", action="store_true", default=False)
        parser.add_argument("platform", nargs="?", default=None)
        return parser

    def run(self, args):
        if args.list:
            for name in platforms.get_platform_names():
                print(name)
        else:
            p = platforms.get_platform(args.platform)
            print("platform:")
            pprint.pprint(p)
            print()

            print("override keys:")
            pprint.pprint(platforms.get_platform_override_keys(p))


class ShowOverrides:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "show-override",
            help="Displays pyproject.toml after override processing",
            parents=[parent_parser],
        )
        parser.add_argument("toml", nargs="?", default="pyproject.toml")
        parser.add_argument(
            "-p",
            "--platform",
            default=None,
            help="Use robotpy-build platform-info --list for available platforms",
        )
        return parser

    def run(self, args):
        p = platforms.get_platform(args.platform)
        override_keys = platforms.get_platform_override_keys(p)

        with open(args.toml, "rb") as fp:
            d = tomli.load(fp)

        overrides.apply_overrides(d, override_keys)
        print(tomli_w.dumps(d))


class MavenParser:
    after_archs = [
        "static",
        "debug",
        "staticdebug",
    ]

    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "parse-maven",
            help="Find supported platforms from a pyproject.toml",
            parents=[parent_parser],
        )
        parser.add_argument(
            "toml_link",
            help="Ex: pyproject.toml",
        )
        parser.add_argument(
            "-b",
            "--brute_force",
            action="store_true",
            help="Try known os and arch combinations instead of parsing html (needed for rev)",
        )
        return parser

    def check_url_exists(self, file_url):
        with suppress(Exception):
            if urlopen(Request(file_url)).code == 200:
                return True
        return False

    def run(self, args):
        self.os_names = set()
        self.arch_names = set()
        for plat in platforms._platforms.values():
            self.os_names.add(plat.os)
            self.arch_names.add(plat.arch)

        with open(args.toml_link, "rb") as fp:
            config = tomli.load(fp)["tool"]["robotpy-build"]

            wrappers = {}
            if "wrappers" in config:
                wrappers = {
                    k: v
                    for (k, v) in config["wrappers"].items()
                    if "maven_lib_download" in v
                }

            static_libs = {}
            if "static_libs" in config:
                static_libs = {
                    k: v
                    for (k, v) in config["static_libs"].items()
                    if "maven_lib_download" in v
                }

            if wrappers == {} and static_libs == {}:
                print("No maven_lib_downloads in pyproject.toml")
                exit()

            for w_name, wrapper in {**wrappers, **static_libs}.items():
                if "maven_lib_download" not in wrapper:
                    continue

                mvl = wrapper["maven_lib_download"]

                repo_url = mvl["repo_url"]
                grp = mvl["group_id"].replace(".", "/")
                art = mvl["artifact_id"]
                ver = mvl["version"]

                dir_url = f"{repo_url}/{grp}/{art}/{ver}/"

                plats = defaultdict(set)

                found_source = False
                source_name = None

                if args.brute_force:
                    for os in self.os_names:
                        for arch in self.arch_names:
                            for after_arch in self.after_archs + [""]:
                                classifier = os + arch + after_arch
                                file_url = f"{dir_url}{art}-{ver}-{classifier}.zip"

                                if self.check_url_exists(file_url):
                                    plats[os].add(arch)

                    if self.check_url_exists(f"{dir_url}{art}-{ver}-source.zip"):
                        found_source = True
                        source_name = "source"

                    if self.check_url_exists(f"{dir_url}{art}-{ver}-sources.zip"):
                        found_source = True
                        source_name = "sources"

                else:
                    try:
                        html = str(urlopen(Request(dir_url)).read())
                    except HTTPError as e:
                        if e.code != 404:
                            raise e
                        else:
                            print(
                                "The repo url returned a 404 error. Try using the brute_force flag."
                            )
                            exit()

                    found_source = False
                    source_name = None

                    if "source.zip" in html:
                        found_source = True
                        source_name = "source"

                    if "sources.zip" in html:
                        found_source = True
                        source_name = "sources"

                    # matches = re.findall('\.zip">(.*?)\.zip</a>', html, re.I) # match on text
                    matches = re.findall('href="(.*?)">', html, re.I)  # match on links
                    matches = [
                        m[:-4] for m in matches if m[-4:] == ".zip"
                    ]  # match on zip files and remove extension

                    for m in matches:
                        for os in self.os_names:
                            idx = m.find(os)

                            if idx != -1:
                                arch = m[idx + len(os) :]

                                for after_arch in self.after_archs:
                                    arch = arch.replace(after_arch, "")

                                plats[os].add(arch)
                                break

                # Formatting
                print()
                print(f"Wrapper / static_lib :: {w_name}")
                print(f"Artifact ID :: {art}")
                print(f"URL :: {dir_url}")
                print()

                if found_source:
                    print("This repo appears to provide sources.")
                    print("The name of the source file is:", source_name)
                    print()

                plat_str = "supported_platforms = [\n"
                for os in plats:
                    for arch in plats[os]:
                        plat_str += '    {{ os = "{}", arch = "{}" }},\n'.format(
                            os, arch
                        )
                plat_str += "]"

                print(plat_str)


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
    exit(main())
