"""
Create YAML files from parsed header files
"""

import argparse
import pathlib
import sys

from .autowrap.generator_data import MissingReporter
from .cmd_header2dat import make_argparser, generate_wrapper
from .makeplan import InputFile, makeplan, BuildTarget


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--write", action="store_true", help="Write to files if they don't exist"
    )
    args = parser.parse_args()

    project_root = pathlib.Path.cwd()

    plan = makeplan(project_root, missing_yaml_ok=True)

    for item in plan:
        if not isinstance(item, BuildTarget) or item.command != "header2dat":
            continue

        # convert args to string so we can parse it
        # .. this is weird, but less annoying than other alternatives
        #    that I can think of?
        argv = []
        for arg in item.args:
            if isinstance(arg, str):
                argv.append(arg)
            elif isinstance(arg, InputFile):
                argv.append(str(arg.path))
            else:
                # anything else shouldn't matter
                argv.append("ignored")

        sparser = make_argparser()
        sargs = sparser.parse_args(argv)

        reporter = MissingReporter()

        generate_wrapper(
            name=sargs.name,
            src_yml=sargs.src_yml,
            src_h=sargs.src_h,
            dst_dat=None,
            dst_depfile=None,
            include_paths=sargs.include_paths,
            casters={},
            pp_defines=sargs.pp_defines,
            missing_reporter=reporter,
            report_only=True,
        )

        if reporter:
            for name, report in reporter.as_yaml():
                report = f"---\n\n{report}"

                nada = False
                if args.write:
                    if not name.exists():
                        print("Writing", name)
                        with open(name, "w") as fp:
                            fp.write(report)
                    else:
                        print(name, "already exists!")

                print("===", name, "===")
                print(report)


if __name__ == "__main__":
    main()
