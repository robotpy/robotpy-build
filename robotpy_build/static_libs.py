import os
from os.path import join
import posixpath
import shutil
from typing import Dict, List, Optional

from .download import download_maven
from .pyproject_configs import StaticLibConfig


class StaticLib:
    # implements pkgcfg

    def __init__(self, name: str, cfg: StaticLibConfig, setup):
        self.name = name
        self.cfg = cfg
        self.static_lib = True
        self.libinit_import = None
        # TODO
        self.depends = []

        self.platform = setup.platform

        self.root: Optional[os.PathLike] = None
        self.incdir: Optional[str] = None
        self.libdir: Optional[str] = None

    def set_root(self, root: os.PathLike) -> None:
        self.root = root
        self.libdir = join(self.root, self.name, "lib")
        self.incdir = join(self.root, self.name, "include")

    def get_include_dirs(self) -> Optional[List[str]]:
        return [self.incdir]

    def get_library_dirs(self) -> Optional[List[str]]:
        return [self.libdir]

    def get_library_dirs_rel(self) -> Optional[List[str]]:
        pass

    def get_library_names(self) -> Optional[List[str]]:
        # don't do this except on Windows
        if self.platform.os != "windows":
            return

        return self._get_libnames(useext=False)

    def get_library_full_names(self) -> Optional[List[str]]:
        pass

    def get_extra_objects(self) -> Optional[List[str]]:
        if self.platform.os == "windows":
            return

        return [join(self.libdir, lib) for lib in self._get_libnames()]

    def get_type_casters(self, casters: Dict[str, str]) -> None:
        pass

    def _get_libnames(self, useext=True):
        mcfg = self.cfg.maven_lib_download
        if mcfg.libs is None:
            libs = [mcfg.artifact_id]
        else:
            libs = mcfg.libs
        ext = ""
        if useext:
            ext = self.platform.staticext
        return [f"{self.platform.libprefix}{lib}{ext}" for lib in libs]

    def on_build_dl(self, cache: str, libdir: str):

        dlcfg = self.cfg.maven_lib_download

        self.set_root(libdir)

        shutil.rmtree(self.libdir, ignore_errors=True)
        shutil.rmtree(self.incdir, ignore_errors=True)

        os.makedirs(self.libdir)

        download_maven(dlcfg, "headers", self.incdir, cache)

        extract_names = self._get_libnames()

        to = {
            posixpath.join(
                self.platform.os, self.platform.arch, "static", libname
            ): join(self.libdir, libname)
            for libname in extract_names
        }

        download_maven(
            dlcfg, f"{self.platform.os}{self.platform.arch}static", to, cache
        )
