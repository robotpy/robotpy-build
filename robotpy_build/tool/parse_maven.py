from collections import defaultdict
from contextlib import suppress
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import tomli

from .. import platforms


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
