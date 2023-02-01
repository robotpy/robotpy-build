#
# Portions copied from pybind11's setup_helpers.py
#

import os
from os.path import join
from setuptools.command.build_ext import build_ext
import platform
import setuptools
import sys
import sysconfig
import tempfile

from .util import get_install_root
from ..platforms import get_platform

# TODO: only works for GCC
debug = os.environ.get("RPYBUILD_DEBUG") == "1"

WIN = sys.platform.startswith("win32") and "mingw" not in sysconfig.get_platform()
MACOS = sys.platform.startswith("darwin")
STD_TMPL = "/std:c++{}" if WIN else "-std=c++{}"


# As of Python 3.6, CCompiler has a `has_flag` method.
# cf http://bugs.python.org/issue26689
def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        fname = join(tmpdir, "test.cpp")
        with open(fname, "w") as fp:
            fp.write("int main (int argc, char **argv) { return 0; }")
        try:
            compiler.compile([fname], output_dir=tmpdir, extra_postargs=[flagname])
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cxx_std(compiler) -> int:
    """Return the -std=c++[11/14/17/20] compiler flag.
    The newer version is prefered over c++11 (when it is available).
    """

    for level in (20, 17, 17, 11):
        if has_flag(compiler, STD_TMPL.format(level)):
            return level

    raise RuntimeError("Unsupported compiler -- at least C++11 support is needed!")


def get_opts(typ, std):
    c_opts = {"msvc": ["/EHsc", "/bigobj"], "unix": []}
    l_opts = {"msvc": [], "unix": []}

    plat = get_platform()
    if plat.os == "osx":
        darwin_opts = ["-stdlib=libc++"]

        if "MACOSX_DEPLOYMENT_TARGET" not in os.environ:
            # C++17 requires a higher min version of macOS. An earlier version
            # (10.12 or 10.13) can be set manually via environment variable if
            # you are careful in your feature usage, but 10.14 is the safest
            # setting for general use. However, never set higher than the
            # current macOS version!
            current_macos = tuple(int(x) for x in platform.mac_ver()[0].split(".")[:2])
            if std == 20:
                desired_macos = (10, 15)
            elif std == 17:
                desired_macos = (10, 14)
            else:
                desired_macos = (10, 9)

            macos_string = ".".join(str(x) for x in min(current_macos, desired_macos))
            darwin_opts.append(f"-mmacosx-version-min={macos_string}")

        c_opts["unix"] += darwin_opts
        l_opts["unix"] += darwin_opts + ["-headerpad_max_install_names"]

    return c_opts.get(typ, []), l_opts.get(typ, [])


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""

    def build_extensions(self):
        ct = self.compiler.compiler_type
        std = cxx_std(self.compiler)
        opts, link_opts = get_opts(ct, std)

        # To support ccache on windows
        cc_launcher = os.environ.get("RPYBUILD_CC_LAUNCHER")

        if ct == "unix":
            opts.append("-s")  # strip
            if debug:
                opts.append("-ggdb3")
                opts.append("-UNDEBUG")
            else:
                opts.append("-g0")  # remove debug symbols
            opts.append(STD_TMPL.format(std))
            if has_flag(self.compiler, "-fvisibility=hidden"):
                opts.append("-fvisibility=hidden")

            if cc_launcher:
                self.compiler.compiler.insert(0, cc_launcher)
                self.compiler.compiler_so.insert(0, cc_launcher)
                # compiler_cxx is only used for linking, so we don't mess with it
                # .. distutils is so weird
                # self.compiler.compiler_cxx.insert(0, cc_launcher)
        elif ct == "msvc":
            opts.append(STD_TMPL.format(std))
            opts.append("/Zc:__cplusplus")
            # Enable standards-compliant preprocessor
            if has_flag(self.compiler, "/Zc:preprocessor"):
                opts.append("/Zc:preprocessor")
            if cc_launcher:
                # yes, this is terrible. There's really no other way with distutils
                def _spawn(cmd):
                    if cmd[0] == self.compiler.cc:
                        cmd.insert(0, cc_launcher)
                    self.compiler._rpy_spawn(cmd)

                self.compiler._rpy_spawn = self.compiler.spawn
                self.compiler.spawn = _spawn
        for ext in self.extensions:
            ext.define_macros.append(("PYBIND11_USE_SMART_HOLDER_AS_DEFAULT", "1"))
            if debug:
                ext.define_macros.append(
                    ("PYBIND11_ASSERT_GIL_HELD_INCREF_DECREF", "1")
                )
            ext.extra_compile_args = opts
            ext.extra_link_args = link_opts

        # self._gather_global_includes()

        build_ext.build_extensions(self)

        # Fix Libraries on macOS
        # Uses @loader_path, is compatible with macOS >= 10.4
        platform = get_platform()
        if platform.os == "osx":
            from ..relink_libs import relink_extension

            install_root = get_install_root(self)

            for ext in self.extensions:
                libs = relink_extension(
                    install_root,
                    self.get_ext_fullpath(ext.name),
                    self.get_ext_filename(ext.name),
                    ext.rpybuild_wrapper,
                    self.rpybuild_pkgcfg,
                )

                # Used in build_pyi
                ext.rpybuild_libs = libs

    def run(self):
        # files need to be generated before building can occur
        self.run_command("build_gen")

        for wrapper in self.wrappers:
            wrapper.finalize_extension()

        build_ext.run(self)

        # pyi can only be built after ext is built
        self.run_command("build_pyi")

    def get_libraries(self, ext):
        libraries = build_ext.get_libraries(self, ext)

        if (
            sys.platform != "win32"
            and os.environ.get("RPYBUILD_STRIP_LIBPYTHON") == "1"
        ):
            pythonlib = "python{}.{}".format(
                sys.hexversion >> 24, (sys.hexversion >> 16) & 0xFF
            )
            libraries = [lib for lib in libraries if not lib.startswith(pythonlib)]

        return libraries


parallel = int(os.environ.get("RPYBUILD_PARALLEL", "0"))
if parallel > 0:
    # don't enable this hack by default, because not really sure of the
    # ramifications -- however, it's really useful for development
    #
    # .. the real answer to this is cmake o_O

    # monkey-patch for parallel compilation
    # -> https://stackoverflow.com/questions/11013851/speeding-up-build-process-with-distutils/13176803#13176803
    def parallelCCompile(
        self,
        sources,
        output_dir=None,
        macros=None,
        include_dirs=None,
        debug=0,
        extra_preargs=None,
        extra_postargs=None,
        depends=None,
    ):
        # those lines are copied from distutils.ccompiler.CCompiler directly
        macros, objects, extra_postargs, pp_opts, build = self._setup_compile(
            output_dir, macros, include_dirs, sources, depends, extra_postargs
        )
        cc_args = self._get_cc_args(pp_opts, debug, extra_preargs)
        # parallel code
        import multiprocessing
        import multiprocessing.pool

        N = multiprocessing.cpu_count() if parallel == 1 else parallel

        def _single_compile(obj):
            try:
                src, ext = build[obj]
            except KeyError:
                return
            self._compile(obj, src, ext, cc_args, extra_postargs, pp_opts)

        for _ in multiprocessing.pool.ThreadPool(N).imap(_single_compile, objects):
            pass
        return objects

    import distutils.ccompiler

    distutils.ccompiler.CCompiler.compile = parallelCCompile
