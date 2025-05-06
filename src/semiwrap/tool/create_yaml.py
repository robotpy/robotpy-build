import os
import pathlib
import typing as T

from ..autowrap.generator_data import MissingReporter
from ..cmd.header2dat import make_argparser, generate_wrapper
from ..makeplan import InputFile, makeplan, BuildTarget


class GenCreator:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "create-yaml",
            help="Create YAML files from parsed header files",
            parents=[parent_parser],
        )
        parser.add_argument(
            "--write", help="Write to files if they don't exist", action="store_true"
        )

        return parser

    def run(self, args):
        project_root = pathlib.Path.cwd()

        # Problem: if another hatchling plugin sets PKG_CONFIG_PATH to include a .pc
        # file, makeplan() will fail to find it, which prevents a semiwrap program
        # from consuming those .pc files.
        #
        # We search for .pc files in the project root by default and add anything found
        # to the PKG_CONFIG_PATH to allow that to work. Probably won't hurt anything?

        pcpaths: T.Set[str] = set()
        for pcfile in project_root.glob("**/*.pc"):
            pcpaths.add(str(pcfile.parent))

        if pcpaths:
            # Add to PKG_CONFIG_PATH so that it can be resolved by other hatchling
            # plugins if desired
            pkg_config_path = os.environ.get("PKG_CONFIG_PATH")
            if pkg_config_path is not None:
                os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(
                    (pkg_config_path, *pcpaths)
                )
            else:
                os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(pcpaths)

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
                    argv.append(str(arg.path.absolute()))
                elif isinstance(arg, pathlib.Path):
                    argv.append(str(arg.absolute()))
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
                src_h_root=sargs.src_h_root,
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

                    if args.write:
                        if not name.exists():
                            name.parent.mkdir(parents=True, exist_ok=True)
                            print("Writing", name)
                            with open(name, "w") as fp:
                                fp.write(report)
                        else:
                            print(name, "already exists!")

                    print("===", name, "===")
                    print(report)
