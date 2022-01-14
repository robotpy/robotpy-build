import os
from os.path import join
import posixpath
import shutil
from typing import Any, Dict, List, Optional

from .download import download_and_extract_zip
from .pyproject_configs import Download, StaticLibConfig


class StaticLib:
    # implements pkgcfg

    def __init__(self, name: str, cfg: StaticLibConfig, setup):
        self.package_name = name
        self.name = name
        self.cfg = cfg
        self.static_lib = True
        self.libinit_import = None
        self.pypi_package = None
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
        includes = [self.incdir]
        if self.cfg.download:
            for dl in self.cfg.download:
                if dl.extra_includes:
                    includes += [join(self.incdir, inc) for inc in dl.extra_includes]
        return includes

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

    def get_type_casters_cfg(self, casters: Dict[str, Dict[str, Any]]) -> None:
        pass

    def _get_dl_libnames(self, dl: Download, useext=True):
        ext = ""
        if useext:
            ext = self.platform.staticext
        return [f"{self.platform.libprefix}{lib}{ext}" for lib in dl.libs]

    def _get_libnames(self, useext=True):
        libs = []
        for dl in self.cfg.download:
            if dl.libs:
                libs += self._get_dl_libnames(dl, useext)
        return libs

    def on_build_dl(self, cache: str, libdir: str):

        self.set_root(libdir)

        shutil.rmtree(self.libdir, ignore_errors=True)
        shutil.rmtree(self.incdir, ignore_errors=True)

        os.makedirs(self.libdir)

        for dl in self.cfg.download:

            if dl.sources is not None:
                raise ValueError(f"{dl.url}: cannot specify sources in static lib")

            if dl.libs is None:
                if dl.incdir is None:
                    raise ValueError(f"{dl.url}: must specify libs in static lib")
                to = {}
            else:
                to = {
                    posixpath.join(dl.libdir, libname): join(self.libdir, libname)
                    for libname in self._get_dl_libnames(dl)
                }

            if dl.incdir is not None:
                to[dl.incdir] = self.incdir

            if dl.dlopenlibs is not None:
                raise ValueError(f"{dl.url}: cannot specify dlopenlibs in static lib")

            download_and_extract_zip(dl.url, to, cache)
