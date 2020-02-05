from distutils.core import Command
from typing import List
import os.path

from ..platforms import get_platform
from ..static_libs import StaticLib
from ..wrapper import Wrapper
from .util import get_install_root


class BuildDl(Command):

    command_name = "build_dl"
    description = "Downloads files"
    user_options = [
        ("build-base=", "b", "base directory for build library"),
        ("build-temp=", "t", "temporary build directory"),
        ("build-cache=", None, "build directory to cache downloaded objects"),
        ("src-unpack-to=", None, "build directory to unpack sources to"),
        ("lib-unpack-to=", None, "build directory to unpack static libs to"),
    ]
    wrappers: List[Wrapper] = []
    static_libs: List[StaticLib] = []

    def initialize_options(self):
        self.build_base = None
        self.build_cache = None
        self.build_temp = None
        self.src_unpack_to = None
        self.lib_unpack_to = None

    def finalize_options(self):
        self.set_undefined_options(
            "build", ("build_base", "build_base"), ("build_temp", "build_temp")
        )
        if self.build_cache is None:
            self.build_cache = os.path.join(self.build_base, "cache")
        if self.src_unpack_to is None:
            self.src_unpack_to = os.path.join(self.build_temp, "dlsrc")
        if self.lib_unpack_to is None:
            self.lib_unpack_to = os.path.join(self.build_temp, "dlstatic")

    def run(self):
        for lib in self.static_libs:
            lib.on_build_dl(self.build_cache, self.lib_unpack_to)
        for wrapper in self.wrappers:
            wrapper.on_build_dl(self.build_cache, self.src_unpack_to)

        # On OSX, fix library loader paths for embedded libraries
        # -> this happens here so that the libs are modified before build_py
        #    copies them. Extensions are fixed after build
        platform = get_platform()
        if platform.os == "osx":
            from ..relink_libs import relink_libs

            install_root = get_install_root(self)
            for wrapper in self.wrappers:
                relink_libs(install_root, wrapper, self.rpybuild_pkgcfg)
