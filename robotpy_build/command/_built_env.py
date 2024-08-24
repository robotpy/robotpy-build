import importlib.util
import os
from os.path import abspath, exists, dirname, join

from setuptools import Command

from .util import get_install_root


class _BuiltEnv(Command):

    user_options = [("build-lib=", "d", 'directory to "build" (copy) to')]

    def initialize_options(self):
        self.build_lib = None

    def finalize_options(self):
        self.set_undefined_options("build", ("build_lib", "build_lib"))

    def setup_built_env(self):

        # Gather information for n
        data = {"mapping": {}}

        # OSX-specific: need to set DYLD_LIBRARY_PATH otherwise modules don't
        # work. Luckily, that information was computed when building the
        # extensions...
        env = os.environ.copy()
        dyld_path = set()

        # Requires information from build_ext to work
        build_ext = self.get_finalized_command("build_ext")
        if build_ext.inplace:
            data["out"] = get_install_root(self)
        else:
            data["out"] = self.build_lib

        # Ensure that the associated packages can always be found locally
        for wrapper in build_ext.wrappers:
            pkgdir = wrapper.package_name.split(".")
            init_py = abspath(join(self.build_lib, *pkgdir, "__init__.py"))
            if exists(init_py):
                data["mapping"][wrapper.package_name] = init_py

        # Ensure that the built extension can always be found
        build_ext.resolve_libs()
        for ext in build_ext.extensions:
            fname = build_ext.get_ext_filename(ext.name)
            data["mapping"][ext.name] = abspath(join(self.build_lib, fname))

            rpybuild_libs = getattr(ext, "rpybuild_libs", None)
            if rpybuild_libs:
                for pth, _ in rpybuild_libs.values():
                    dyld_path.add(dirname(pth))

        # OSX-specific
        if dyld_path:
            dyld_path = ":".join(dyld_path)
            if "DYLD_LIBRARY_PATH" in env:
                dyld_path += ":" + env["DYLD_LIBRARY_PATH"]
            env["DYLD_LIBRARY_PATH"] = dyld_path

        return data, env


class _PackageFinder:
    """
    Custom loader to allow loading built modules from their location
    in the build directory (as opposed to their install location)
    """

    # Set this to mapping returned from _BuiltEnv.setup_built_env
    mapping = {}

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        m = cls.mapping.get(fullname)
        if m:
            return importlib.util.spec_from_file_location(fullname, m)
