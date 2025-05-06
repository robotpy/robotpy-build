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
    BuildTargetOutput,
    ExtensionModule,
    LocalDependency,
    CppMacroValue,
    makeplan,
)
from .util import maybe_write_file, relpath_walk_up

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


VarTypes = T.Union[
    InputFile, OutputFile, BuildTarget, ExtensionModule, LocalDependency, CppMacroValue
]


class VarCache:
    def __init__(self) -> None:
        self.cache: T.Dict[VarTypes, str] = {}

        # this might get annoying to debug, but for now this is easier...
        self.idx = 1

    def getvar(self, item: VarTypes) -> str:
        var = self.cache.get(item)
        if var is None:

            # TODO: probably should name variables according to their target type
            # to make it easier to debug

            if isinstance(item, InputFile):
                # .. this probably isn't right either, what should this be relative to?
                # .. TODO should use files()? but maybe only if this is actually a variable
                return _make_string(item.path.resolve().as_posix())
                # var = f"sw_in_{self.idx}"
            elif isinstance(item, OutputFile):
                return _make_string(item.name)
                # var = f"sw_out_{self.idx}"
            elif isinstance(item, BuildTarget):
                var = f"_sw_target_{self.idx}"
            elif isinstance(item, ExtensionModule):
                name = item.name.replace("-", "_")
                var = f"{name}_module"
            elif isinstance(item, LocalDependency):
                name = item.name.replace("-", "_")
                var = f"{name}_dep"
            elif isinstance(item, CppMacroValue):
                name = item.name
                var = f"_sw_cpp_var_{name}"
            else:
                assert False

            self.idx += 1
            self.cache[item] = var
        return var


def _render_build_target(r: RenderBuffer, vc: VarCache, bt: BuildTarget):
    outvar = vc.getvar(bt)

    bt_cmd = bt.command.replace("-", "_")
    cmd = [f"_sw_cmd_{bt_cmd}"]
    tinput = []
    toutput = []
    depfile = None

    for arg in bt.args:
        if isinstance(arg, str):
            cmd.append(_make_string(arg))
        elif isinstance(arg, pathlib.Path):
            cmd.append(_make_string(arg.resolve().as_posix()))
        elif isinstance(arg, (BuildTarget, InputFile)):
            cmd.append(f"'@INPUT{len(tinput)}@'")
            tinput.append(vc.getvar(arg))
        elif isinstance(arg, BuildTargetOutput):
            cmd.append(f"'@INPUT{len(tinput)}@'")
            tinput.append(f"{vc.getvar(arg.target)}[{arg.output_index}]")
        elif isinstance(arg, OutputFile):
            cmd.append(f"'@OUTPUT{len(toutput)}@'")
            toutput.append(vc.getvar(arg))
        elif isinstance(arg, Depfile):
            assert depfile is None, bt
            cmd.append("'@DEPFILE@'")
            depfile = _make_string(arg.name)
        elif isinstance(arg, ExtensionModule):
            cmd.append(f"'@INPUT{len(tinput)}@'")
            tinput.append(vc.getvar(arg))
        elif isinstance(arg, CppMacroValue):
            cmd.append(vc.getvar(arg))
        else:
            assert False, f"unexpected {arg!r} in {bt}"

    r.writeln(f"{outvar} = custom_target(")
    with r.indent(2):
        _render_meson_args(r, "command", cmd)
        if tinput:
            _render_meson_args(r, "input", tinput)
        if toutput:
            _render_meson_args(r, "output", toutput)

        if depfile:
            r.writeln(f"depfile: {depfile},")

        if bt.install_path is not None:
            install_path = _make_string(bt.install_path.as_posix())
            r.writeln(
                f"install_dir: sw_py.get_install_dir(pure: false) / {install_path},"
            )
            r.writeln("install: true,")

    r.writeln(")")


def _render_include_directories(
    r: RenderBuffer,
    incs: T.Sequence[pathlib.Path],
    meson_build_path: T.Optional[pathlib.Path],
):
    # meson wants these to be relative to meson.build
    # - only can do that if we're writing an output file
    if meson_build_path:
        meson_build_parent = meson_build_path.parent
        incs = [relpath_walk_up(p, meson_build_parent) for p in incs]

    _render_meson_args(
        r, "include_directories", [_make_string(inc.as_posix()) for inc in incs]
    )


def _render_meson_args(r: RenderBuffer, name: str, args: T.List[str]):
    r.writeln(f"{name}: [")
    with r.indent():
        for arg in args:
            r.writeln(f"{arg},")
    r.writeln("],")


def _render_module_stage0(
    r: RenderBuffer,
    vc: VarCache,
    m: ExtensionModule,
    meson_build_path: T.Optional[pathlib.Path],
):

    # variables generated here should be deterministic so that users can add
    # their own things to it, or use it directly

    r.writeln(f"# {m.package_name}")
    r.writeln(f"{m.name}_sources = []")
    r.writeln(f"{m.name}_deps = [declare_dependency(")
    with r.indent():

        if m.sources:
            r.writeln("sources: [")
            with r.indent():
                for src in m.sources:
                    r.writeln(f"{vc.getvar(src)},")

            r.writeln("],")

        if m.depends:
            depnames = []
            for d in m.depends:
                if isinstance(d, LocalDependency):
                    depnames.append(vc.getvar(d))
                else:
                    depnames.append(f"dependency({_make_string(d)})")

            deps = ", ".join(depnames)
            r.writeln(f"dependencies: [{deps}],")

        if m.include_directories:
            _render_include_directories(r, m.include_directories, meson_build_path)

    r.writeln(")]")


def _render_module_stage1(
    r: RenderBuffer,
    vc: VarCache,
    m: ExtensionModule,
    meson_build_path: T.Optional[pathlib.Path],
):

    # variables generated here should be deterministic so that users can
    # use it directly if they wish

    subdir = _make_string(m.install_path.as_posix())
    module_name = _make_string(m.package_name.split(".")[-1])
    mvar = vc.getvar(m)

    r.writeln(f"# {m.package_name}")
    r.writeln(f"{mvar} = sw_py.extension_module(")
    with r.indent():
        r.write_trim(
            f"""
            {module_name},
            sources: [{m.name}_sources],
            dependencies: [{m.name}_deps],
            install: true,
            subdir: {subdir},        
        """
        )

        if m.include_directories:
            _render_include_directories(r, m.include_directories, meson_build_path)

    r.writeln(")")
    r.writeln()


def render_meson(
    project_root: pathlib.Path,
    stage0_path: T.Optional[pathlib.Path],
    stage1_path: T.Optional[pathlib.Path],
    trampolines_path: T.Optional[pathlib.Path],
) -> T.Tuple[str, str, str, T.List[Entrypoint]]:
    """
    Returns the contents of two meson.build files that build on each other, and
    any entry points that need to be created
    """

    eps: T.List[Entrypoint] = []

    r0 = RenderBuffer()
    r1 = RenderBuffer()
    t = RenderBuffer()
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
        _sw_cmd_gen_libinit_py = [sw_py, '-m', 'semiwrap.cmd.gen_libinit']
        _sw_cmd_gen_pkgconf = [sw_py, '-m', 'semiwrap.cmd.gen_pkgconf']
        _sw_cmd_publish_casters = [sw_py, '-m', 'semiwrap.cmd.publish_casters']
        _sw_cmd_resolve_casters = [sw_py, '-m', 'semiwrap.cmd.resolve_casters']
        _sw_cmd_header2dat = [sw_py, '-m', 'semiwrap.cmd.header2dat']
        _sw_cmd_dat2cpp = [sw_py, '-m', 'semiwrap.cmd.dat2cpp']
        _sw_cmd_dat2trampoline = [sw_py, '-m', 'semiwrap.cmd.dat2trampoline']
        _sw_cmd_dat2tmplcpp = [sw_py, '-m', 'semiwrap.cmd.dat2tmplcpp']
        _sw_cmd_dat2tmplhpp = [sw_py, '-m', 'semiwrap.cmd.dat2tmplhpp']
        _sw_cmd_gen_modinit_hpp = [sw_py, '-m', 'semiwrap.cmd.gen_modinit_hpp']
        _sw_cmd_make_pyi = [sw_py, '-m', 'semiwrap.cmd.make_pyi']

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
    macros: T.List[CppMacroValue] = []
    build_targets: T.List[BuildTarget] = []
    modules: T.List[ExtensionModule] = []
    pyi_targets: T.List[BuildTarget] = []
    local_deps: T.List[LocalDependency] = []
    trampoline_targets: T.List[BuildTarget] = []

    for item in plan:
        if isinstance(item, BuildTarget):
            if item.command == "make-pyi":
                # defer these to the end
                pyi_targets.append(item)
            elif item.command == "dat2trampoline":
                trampoline_targets.append(item)
            else:
                build_targets.append(item)
        elif isinstance(item, ExtensionModule):
            # defer these to the end
            modules.append(item)
        elif isinstance(item, Entrypoint):
            eps.append(item)
        elif isinstance(item, LocalDependency):
            local_deps.append(item)
        elif isinstance(item, CppMacroValue):
            macros.append(item)
        else:
            assert False

    if macros:
        for macro in macros:
            macro_name = _make_string(macro.name)
            r0.writeln(
                f"{vc.getvar(macro)} = meson.get_compiler('cpp').get_define({macro_name})"
            )
        r0.writeln()

    for target in build_targets:
        _render_build_target(r0, vc, target)

    if local_deps:
        r0.writeln()
        r0.write_trim(
            """
            #
            # Local dependencies
            #
        """
        )
        for ld in local_deps:
            r0.writeln(f"{vc.getvar(ld)} = declare_dependency(")
            with r0.indent():
                if ld.depends:
                    deps = []
                    for dep in ld.depends:
                        if isinstance(dep, LocalDependency):
                            deps.append(vc.getvar(dep))
                        else:
                            deps.append(f"dependency({_make_string(dep)})")

                    depstrs = ", ".join(deps)
                    r0.writeln(f"dependencies: [{depstrs}],")

                if ld.include_paths:
                    _render_include_directories(r0, ld.include_paths, stage0_path)

            r0.writeln(")")

    if trampoline_targets:
        t.writeln("# This file is automatically generated, DO NOT EDIT\n\n")
        for target in trampoline_targets:
            _render_build_target(t, vc, target)

        r0.writeln()
        r0.writeln("subdir('trampolines')")

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
            _render_module_stage0(r0, vc, module, stage0_path)
            _render_module_stage1(r1, vc, module, stage1_path)

        # TODO: this conditional probably should be done in meson instead
        # cannot build pyi files when cross-compiling
        if not (
            "_PYTHON_HOST_PLATFORM" in os.environ
            or "PYTHON_CROSSENV" in os.environ
            or os.environ.get("SEMIWRAP_SKIP_PYI") == "1"
        ):
            for target in pyi_targets:
                _render_build_target(r1, vc, target)

    return r0.getvalue(), r1.getvalue(), t.getvalue(), eps


def render_meson_to_file(
    project_root: pathlib.Path,
    stage0: pathlib.Path,
    stage1: pathlib.Path,
    trampolines: pathlib.Path,
) -> T.List[Entrypoint]:

    # because of https://github.com/mesonbuild/meson/issues/2320
    assert trampolines.parent.parent == stage0.parent

    s0_content, s1_content, t_content, eps = render_meson(
        pathlib.Path(project_root), stage0, stage1, trampolines
    )

    maybe_write_file(stage0, s0_content, encoding="utf-8")
    maybe_write_file(stage1, s1_content, encoding="utf-8")
    maybe_write_file(trampolines, t_content, encoding="utf-8")

    return eps


def main():
    def _usage() -> T.NoReturn:
        print(f"{sys.argv[0]} project_root stage0 [stage1]", file=sys.stderr)
        sys.exit(1)

    # this entrypoint only for debugging
    try:
        _, project_root = sys.argv
    except ValueError:
        _usage()

    s0_content, s1_content, t_content, _ = render_meson(
        pathlib.Path(project_root), None, None, None
    )

    print(s0_content)
    print("\n---\n")
    print(s1_content)
    print("\n---\n")
    print(t_content)


if __name__ == "__main__":
    main()
