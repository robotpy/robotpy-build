"""
Parses a header file and writes an intermediate dat file that other tools
can turn into other things
"""

import argparse
import os
import pathlib
import pickle
import typing

from cxxheaderparser.options import ParserOptions
from cxxheaderparser import preprocessor

from ..autowrap.cxxparser import parse_header
from ..autowrap.generator_data import GeneratorData, MissingReporter
from ..casters import CastersData
from ..config.autowrap_yml import AutowrapConfigYaml

# TODO: eventually provide native preprocessor by default and allow it
#       to be enabled/disabled per-file just in case
# TODO: should this also be a command line option?
if os.getenv("SEMIWRAP_PP_GCC") == "1":
    # GCC preprocessor can be 10x faster than pcpp for very complex files
    def make_preprocessor(*args, **kwargs):
        return preprocessor.make_gcc_preprocessor(print_cmd=False, *args, **kwargs)

else:
    make_preprocessor = preprocessor.make_pcpp_preprocessor


def generate_wrapper(
    *,
    name: str,
    src_yml: pathlib.Path,
    src_h: pathlib.Path,
    src_h_root: pathlib.Path,
    include_paths: typing.List[pathlib.Path],
    pp_defines: typing.List[str],
    casters: CastersData,
    dst_dat: typing.Optional[pathlib.Path],
    dst_depfile: typing.Optional[pathlib.Path],
    missing_reporter: MissingReporter,
    report_only: bool,
):

    try:
        # semiwrap requires user to create yaml files first using create-yaml
        data = AutowrapConfigYaml.from_file(src_yml)
    except FileNotFoundError:
        if not report_only:
            raise

        print("WARNING: could not find", src_yml)
        data = AutowrapConfigYaml()

    deptarget = None
    if dst_depfile is not None:
        assert dst_dat is not None
        deptarget = [str(dst_dat)]

    popts = ParserOptions(
        preprocessor=make_preprocessor(
            defines=pp_defines,
            include_paths=include_paths,
            encoding=data.encoding,
            depfile=dst_depfile,
            deptarget=deptarget,
        )
    )

    gendata = GeneratorData(data, src_yml)

    try:
        hctx = parse_header(
            name,
            src_h,
            src_h_root,
            gendata,
            popts,
            casters,
            report_only,
        )
    except Exception as e:
        raise ValueError(f"processing {src_h}") from e

    gendata.report_missing(src_yml, missing_reporter)

    if not report_only and missing_reporter and not data.defaults.ignore:
        print("WARNING: some items not in", src_yml, "for", src_h)
        for name, contents in missing_reporter.as_yaml():
            print(contents)

    if dst_dat is not None:
        with open(dst_dat, "wb") as fp:
            pickle.dump(hctx, fp)


def make_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-I", "--include-paths", action="append", default=[])
    parser.add_argument("-D", "--pp-defines", action="append", default=[])
    parser.add_argument("--cpp")
    parser.add_argument("name")
    parser.add_argument("src_yml", type=pathlib.Path)
    parser.add_argument("src_h", type=pathlib.Path)
    parser.add_argument("src_h_root", type=pathlib.Path)
    parser.add_argument("in_casters", type=pathlib.Path)
    parser.add_argument("dst_dat", type=pathlib.Path)
    parser.add_argument("dst_depfile", type=pathlib.Path)
    return parser


def main():
    parser = make_argparser()
    args = parser.parse_args()

    with open(args.in_casters, "rb") as fp:
        casters = pickle.load(fp)

    if args.cpp:
        args.pp_defines.append(f"__cplusplus {args.cpp}")

    generate_wrapper(
        name=args.name,
        src_yml=args.src_yml,
        src_h=args.src_h,
        src_h_root=args.src_h_root,
        dst_dat=args.dst_dat,
        dst_depfile=args.dst_depfile,
        include_paths=args.include_paths,
        casters=casters,
        pp_defines=args.pp_defines,
        missing_reporter=MissingReporter(),
        report_only=False,
    )


if __name__ == "__main__":
    main()
