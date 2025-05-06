import subprocess
import sys
import tomli


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
        with open("pyproject.toml", "rb") as fp:
            pyproject = tomli.load(fp)
        requirements = pyproject.get("build-system", {}).get("requires", [])

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
