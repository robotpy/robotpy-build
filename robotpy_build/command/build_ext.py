from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import setuptools

from ..platforms import get_platform

# As of Python 3.6, CCompiler has a `has_flag` method.
# cf http://bugs.python.org/issue26689
def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".cpp") as f:
        f.write("int main (int argc, char **argv) { return 0; }")
        try:
            compiler.compile([f.name], extra_postargs=[flagname])
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cpp_flag(compiler):
    """Return the -std=c++[11/14/17] compiler flag.
    The newer version is prefered over c++11 (when it is available).
    """
    flags = ["-std=c++17", "-std=c++14", "-std=c++11"]

    for flag in flags:
        if has_flag(compiler, flag):
            return flag

    raise RuntimeError("Unsupported compiler -- at least C++11 support is needed!")

def get_opts(typ):
    c_opts = {"msvc": ["/EHsc"], "unix": []}
    l_opts = {"msvc": [], "unix": []}

    platform = get_platform()
    if platform.os == "osx":
        darwin_opts = ["-stdlib=libc++", "-mmacosx-version-min=10.7"]
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
            opts.append('-DVERSION_INFO="%s"' % self.distribution.get_version())
            opts.append(cpp_flag(self.compiler))
            if has_flag(self.compiler, "-fvisibility=hidden"):
                opts.append("-fvisibility=hidden")
        elif ct == "msvc":
            opts.append('/DVERSION_INFO=\\"%s\\"' % self.distribution.get_version())
        for ext in self.extensions:
            ext.extra_compile_args = opts
            ext.extra_link_args = link_opts

        # self._gather_global_includes()

        build_ext.build_extensions(self)

    def run(self):

        # files need to be generated before building can occur
        self.run_command("build_gen")

        build_ext.run(self)


# ext_modules = [
#     Extension(
#         "python_example",
#         ["src/main.cpp"],
#         include_dirs=[
#             # include dirs: iterate robotpy-build entrypoints, retrieve
#         ],
#         # library_dirs=
#         # libraries=
#         language="c++",
#     )
# ]

