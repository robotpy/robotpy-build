import os
from os.path import join
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import setuptools
import tempfile

from ..platforms import get_platform

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


def cpp_flag(compiler, pfx, sep="="):
    """Return the -std=c++[11/14/17] compiler flag.
    The newer version is prefered over c++11 (when it is available).
    """

    flags = [f"{pfx}std{sep}c++17", f"{pfx}std{sep}c++14", f"{pfx}std{sep}c++11"]

    for flag in flags:
        if has_flag(compiler, flag):
            return flag

    raise RuntimeError("Unsupported compiler -- at least C++11 support is needed!")


def get_opts(typ):
    c_opts = {"msvc": ["/EHsc"], "unix": []}
    l_opts = {"msvc": [], "unix": []}

    platform = get_platform()
    if platform.os == "osx":
        darwin_opts = ["-stdlib=libc++", "-mmacosx-version-min=10.14"]
        c_opts["unix"] += darwin_opts
        l_opts["unix"] += darwin_opts

    return c_opts.get(typ, []), l_opts.get(typ, [])


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""

    def build_extensions(self):
        ct = self.compiler.compiler_type
        opts, link_opts = get_opts(ct)

        if ct == "unix":
            opts.append("-s")  # strip
            opts.append("-g0")  # remove debug symbols
            opts.append(cpp_flag(self.compiler, "-"))
            if has_flag(self.compiler, "-fvisibility=hidden"):
                opts.append("-fvisibility=hidden")
        elif ct == "msvc":
            opts.append(cpp_flag(self.compiler, "/", ":"))
        for ext in self.extensions:
            ext.extra_compile_args = opts
            ext.extra_link_args = link_opts

        # self._gather_global_includes()

        build_ext.build_extensions(self)
        
        # Fix Libraries on macOS
        # Uses @loader_path, is compatible with macOS >= 10.4
        platform = get_platform()
        if platform.os == 'osx':
            from ..relink_libs import redirect_links, get_build_path
            redirect_links(
                get_build_path(
                    self.extensions[0].name,
                    self.build_lib
                ),
                self.macos_lib_locations
            )

    def run(self):

        # files need to be generated before building can occur
        self.run_command("build_gen")

        build_ext.run(self)


if os.environ.get("RPYBUILD_PARALLEL") == "1":
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

        N = multiprocessing.cpu_count()

        def _single_compile(obj):
            try:
                src, ext = build[obj]
            except KeyError:
                return
            self._compile(obj, src, ext, cc_args, extra_postargs, pp_opts)

        # convert to list, imap is evaluated on-demand
        list(multiprocessing.pool.ThreadPool(N).imap(_single_compile, objects))
        return objects

    import distutils.ccompiler

    distutils.ccompiler.CCompiler.compile = parallelCCompile
