from distutils.core import Command
from typing import List
import os
import os.path
import subprocess
import sys
import sysconfig

from ..platforms import get_platform
from ..static_libs import StaticLib
from ..wrapper import Wrapper
from .util import get_install_root


debug = os.environ.get("RPYBUILD_DEBUG") == "1"


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
        all_libs = []

        for lib in self.static_libs:
            lib.on_build_dl(self.build_cache, self.lib_unpack_to)
        for wrapper in self.wrappers:
            all_libs += wrapper.on_build_dl(self.build_cache, self.src_unpack_to)

        # On OSX, fix library loader paths for embedded libraries
        # -> this happens here so that the libs are modified before build_py
        #    copies them. Extensions are fixed after build
        platform = get_platform()
        if platform.os == "osx":
            from ..relink_libs import relink_libs

            install_root = get_install_root(self)
            for wrapper in self.wrappers:
                relink_libs(install_root, wrapper, self.rpybuild_pkgcfg)

        elif not debug and platform.os == "linux":
            # strip any downloaded libraries
            strip_exe = "strip"
            if getattr(sys, "cross_compiling", False):
                # This is a hack, but the information doesn't seem to be available
                # in other accessible ways
                ar_exe = sysconfig.get_config_var("AR")
                if ar_exe.endswith("-ar"):
                    strip_exe = f"{ar_exe[:-3]}-strip"

            for lib in all_libs:
                print(strip_exe, lib)
                subprocess.check_call([strip_exe, lib])
