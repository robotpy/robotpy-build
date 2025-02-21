from __future__ import annotations

import codecs
import os
import pathlib
import re
import sys
import typing as T

from .autowrap.buffer import RenderBuffer
from .makeplan import (
    Depfile,
    Entrypoint,
    InputFile,
    OutputFile,
    BuildTarget,
    Module,
    makeplan,
)
from .util import maybe_write_file

# String escaping stolen from meson source code, Apache 2.0 license
# This is the regex for the supported escape sequences of a regular string
# literal, like 'abc\x00'
ESCAPE_SEQUENCE_SINGLE_RE = re.compile(
    r"""
    ( \\U[A-Fa-f0-9]{8}   # 8-digit hex escapes
    | \\u[A-Fa-f0-9]{4}   # 4-digit hex escapes
    | \\x[A-Fa-f0-9]{2}   # 2-digit hex escapes
    | \\[0-7]{1,3}        # Octal escapes
    | \\N\{[^}]+\}        # Unicode characters by name
    | \\[\\'abfnrtv]      # Single-character escapes
    )""",
    re.UNICODE | re.VERBOSE,
)


def _decode_match(match: T.Match[str]) -> str:
    return codecs.decode(match.group(0).encode(), "unicode_escape")


def _make_string(s: str):
    s = ESCAPE_SEQUENCE_SINGLE_RE.sub(_decode_match, s)
    return f"'{s}'"


class VarCache:
    def __init__(self) -> None:
        self.cache: T.Dict[T.Union[InputFile, OutputFile, BuildTarget], str] = {}

        # this might get annoying to debug, but for now this is easier...
        self.idx = 1

    def getvar(self, item: T.Union[InputFile, OutputFile, BuildTarget]) -> str:
        var = self.cache.get(item)
        if var is None:

            # TODO: probably should name variables according to their target type
            # to make it easier to debug

            if isinstance(item, InputFile):
                # .. this probably isn't right either, what should this be relative to?
                # .. TODO should use files()? but maybe only if this is actually a variable
                return _make_string(str(item.path.absolute()))
                # var = f"sw_in_{self.idx}"
            elif isinstance(item, OutputFile):
                return _make_string(item.name)
                # var = f"sw_out_{self.idx}"
            elif isinstance(item, BuildTarget):
                var = f"sw_target_{self.idx}"
            else:
                assert False

            # All variables are private
            var = f"_{var}"

            self.idx += 1
            self.cache[item] = var
        return var


def _render_build_target(r: RenderBuffer, vc: VarCache, bt: BuildTarget):
    outvar = vc.getvar(bt)

    cmd = [f"_sw_cmd_{bt.command.replace("-", "_")}"]
    tinput = []
    toutput = []
    depfile = None

    for arg in bt.args:
        if isinstance(arg, str):
            cmd.append(_make_string(arg))
        elif isinstance(arg, pathlib.Path):
            cmd.append(_make_string(str(arg.absolute())))
        elif isinstance(arg, (BuildTarget, InputFile)):
            cmd.append(f"'@INPUT{len(tinput)}@'")
            tinput.append(vc.getvar(arg))
        elif isinstance(arg, OutputFile):
            cmd.append(f"'@OUTPUT{len(toutput)}@'")
            toutput.append(vc.getvar(arg))
        elif isinstance(arg, Depfile):
            assert depfile is None, bt
            cmd.append("'@DEPFILE@'")
            depfile = _make_string(arg.name)
        else:
            assert False, f"unexpected {arg!r} in {bt}"

    r.writeln(f"{outvar} = custom_target(")
    with r.indent(2):

        r.writeln(f"command: [{', '.join(cmd)}],")
        if tinput:
            r.writeln(f"input: [{', '.join(tinput)}],")
        if toutput:
            r.writeln(f"output: [{', '.join(toutput)}],")

        if depfile:
            r.writeln(f"depfile: {depfile},")

        if bt.install_path is not None:
            install_path = _make_string(bt.install_path.as_posix())
            r.writeln(
                f"install_dir: sw_py.get_install_dir(pure: false) / {install_path},"
            )
            r.writeln("install: true,")

    r.writeln(")")


def _render_module_stage0(r: RenderBuffer, vc: VarCache, m: Module):

    # variables generated here should be deterministic so that users can add
    # their own things to it, or use it directly

    r.writeln(f"# {m.package_name}")
    r.writeln(f"{m.name}_module_sources = []")
    r.writeln(f"{m.name}_module_deps = [declare_dependency(")
    with r.indent():

        if m.sources:
            r.writeln("sources: [")
            with r.indent():
                for src in m.sources:
                    r.writeln(f"{vc.getvar(src)},")

            r.writeln("],")

        if m.depends:
            deps = ",".join(f"dependency({_make_string(d)})" for d in m.depends)
            r.writeln(f"dependencies: [{deps}],")

    r.writeln(")]")


def _render_module_stage1(r: RenderBuffer, vc: VarCache, m: Module):

    # variables generated here should be deterministic so that users can
    # use it directly if they wish

    subdir = _make_string(m.install_path.as_posix())
    package_name = _make_string(m.package_name)

    r.writeln(f"# {m.package_name}")
    r.writeln(f"{m.name}_module = sw_py.extension_module(")
    with r.indent():
        r.write_trim(
            f"""
            '_{m.name}',
            sources: [{m.name}_module_sources],
            dependencies: [{m.name}_module_deps],
            install: true,
            subdir: {subdir},        
        """
        )
    r.writeln(")")
    r.writeln()

    # TODO: this conditional probably should be done in meson instead
    # cannot build pyi files when cross-compiling
    if not (
        "_PYTHON_HOST_PLATFORM" in os.environ
        or "PYTHON_CROSSENV" in os.environ
        or os.environ.get("RPYBUILD_SKIP_PYI") == "1"
    ):
        # TODO: this should probably be generated by makeplan, but that makes
        #       separating stage0/stage1 awkward
        r.writeln(f"{m.name}_module_pyi = custom_target(")
        with r.indent():
            r.write_trim(
                f"""
                '{m.name}_module_pyi',
                command: [_sw_cmd_make_pyi, {package_name}, '@OUTPUT0@'],
                depends: [{m.name}_module],
                output: ['_{m.name}.pyi'],
                install: true,
                install_dir: sw_py.get_install_dir(pure: false) / {subdir},
            """
            )

        r.writeln(")")


def gen_meson(project_root: pathlib.Path) -> T.Tuple[str, str, T.List[Entrypoint]]:
    """
    Returns the contents of two meson.build files that build on each other, and
    any entry points that need to be created
    """

    eps: T.List[Entrypoint] = []

    r0 = RenderBuffer()
    r1 = RenderBuffer()
    vc = VarCache()

    # standard boilerplate here
    r0.write_trim(
        """
       # This file is automatically generated, DO NOT EDIT
       #
       # The generator's stable API includes variables that do not start with
       # an underscore. Any variables with an underscore may change in the future
       # without warning
       #
                 
        sw_py = import('python').find_installation()
        
        # internal commands for the autowrap machinery
        _sw_cmd_gen_libinit_py = [sw_py, '-m', 'robotpy_build.cmd_gen_libinit']
        #_sw_cmd_make_pc = [sw_py, '-m', 'robotpy_build.cmd_make_pc']
        _sw_cmd_resolve_casters = [sw_py, '-m', 'robotpy_build.cmd_resolve_casters']
        _sw_cmd_header2dat = [sw_py, '-m', 'robotpy_build.cmd_header2dat']
        _sw_cmd_dat2cpp = [sw_py, '-m', 'robotpy_build.cmd_dat2cpp']
        _sw_cmd_dat2trampoline = [sw_py, '-m', 'robotpy_build.cmd_dat2trampoline']
        _sw_cmd_dat2tmplcpp = [sw_py, '-m', 'robotpy_build.cmd_dat2tmplcpp']
        _sw_cmd_gen_modinit_hpp = [sw_py, '-m', 'robotpy_build.cmd_gen_modinit_hpp']
        _sw_cmd_make_pyi = [sw_py, '-m', 'robotpy_build.cmd_make_pyi']

        #
        # internal custom targets for generating wrappers
        #
    """
    )
    r0.writeln()

    # ... so, we could write out proper loops and stuff to make the output
    #     meson file easier to read, but I think expanded custom targets
    #     is simpler to generate

    plan = makeplan(pathlib.Path(project_root))
    modules: T.List[Module] = []

    for item in plan:
        if isinstance(item, BuildTarget):
            _render_build_target(r0, vc, item)
        elif isinstance(item, Module):
            # defer these to the end
            modules.append(item)
        elif isinstance(item, Entrypoint):
            eps.append(item)
        else:
            assert False

    if modules:
        r0.writeln()
        r0.write_trim(
            """
           #
           # Module configurations
           #
        """
        )
        r0.writeln()

        r1.writeln("# This file is automatically generated, DO NOT EDIT\n\n")

        for module in modules:
            _render_module_stage0(r0, vc, module)
            _render_module_stage1(r1, vc, module)

    return r0.getvalue(), r1.getvalue(), eps


def gen_meson_to_file(
    project_root: pathlib.Path, stage0: pathlib.Path, stage1: pathlib.Path
) -> T.List[Entrypoint]:
    s0_content, s1_content, eps = gen_meson(pathlib.Path(project_root))

    maybe_write_file(stage0, s0_content)
    maybe_write_file(stage1, s1_content)

    return eps


def main():
    def _usage() -> T.NoReturn:
        print(f"{sys.argv[0]} project_root stage0 [stage1]", file=sys.stderr)
        sys.exit(1)

    # this entrypoint only for debugging
    s0_outfile = None
    s1_outfile = None
    try:
        _, project_root, s0_outfile, s1_outfile = sys.argv
    except ValueError:
        try:
            _, project_root, s0_outfile = sys.argv
        except ValueError:
            _usage()

    s0_content, s1_content, _ = gen_meson(pathlib.Path(project_root))
    if s0_outfile == "-":
        print(s0_content)
        print("\n---\n")
        print(s1_content)
        return
    elif s1_outfile is None:
        _usage()

    maybe_write_file(pathlib.Path(s0_outfile), s0_content)
    maybe_write_file(pathlib.Path(s1_outfile), s1_content)


if __name__ == "__main__":
    main()
