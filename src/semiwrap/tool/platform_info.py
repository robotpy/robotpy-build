import pprint

from .. import platforms


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
