from os.path import exists

from .util import get_setup
from ..autowrap.generator_data import MissingReporter


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
