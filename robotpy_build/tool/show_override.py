import tomli
import tomli_w

from .. import overrides
from .. import platforms


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
