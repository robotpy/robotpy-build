"""
    On OSX, the loader does not look at the current process to load
    dylibs -- it insists on finding them itself, so we have to fixup
    our binaries such that they resolve correctly.
    
    Two cases we need to deal with
    - Local development/installation
    - Building a wheel for pypi
    
    In development, we assume things are installed exactly where they will be
    at runtime.
      -> @loader_path/{relpath(final_location, dep_path)}
    
    For pypi wheels, we assume that installation is in site-packages, and
    so are the libraries that this lib depends on.
      -> @loader_path/{relpath(final_siterel, dep_siterel)}
    
    Notice these are the same IF you only build wheels in a virtualenv
    that only has its dependencies installed in site-packages
    

    .. warning:: This will only work for the environment it's compiled in!
                 This basically means don't compile wheels in your development 
                 environment, use a clean environment instead

"""


from delocate.delocating import filter_system_libs
from delocate.tools import get_install_names, set_install_name as _set_install_name

from os import path

from typing import Dict, List, Optional, Tuple

from .pkgcfg_provider import PkgCfg, PkgCfgProvider


def set_install_name(file: str, old_install_name: str, new_install_name: str):
    """Change the install name for a library

    :param file: path to a executable/library file
    :param old_install_name: current path to dependency
    :param new_install_name: new path to dependency
    """

    # This function just calls delocate's set_install_name which uses install_name_tool.
    # This function exists in case we want to change the implementation.

    _set_install_name(file, old_install_name, new_install_name)
    print("Relink:", file, ":", old_install_name, "->", new_install_name)


# Common data structure used here
# - key is basename of library file
# - Value tuple has two pieces:
#   - 0: Where the library file really is right now
#   - 1: Where the library file will be when installed
LibsDict = Dict[str, Tuple[str, str]]


def _resolve_libs(libpaths: Optional[List[str]], libname_full: str, libs: LibsDict):
    if not libpaths:
        return
    for libpath in libpaths:
        p = path.join(libpath, libname_full)
        if path.exists(p):
            libs[libname_full] = (p, p)
            return


def _resolve_libs_in_self(dep: PkgCfg, install_root: str, libs: LibsDict):
    pkgroot = path.join(install_root, *dep.package_name.split("."))
    full_names = dep.get_library_full_names()
    if not full_names:
        return
    for libname_full in full_names:
        for ld, ldr in zip(dep.get_library_dirs(), dep.get_library_dirs_rel()):
            p = path.join(ld, libname_full)
            if path.exists(p):
                # stores where it will exist
                libs[libname_full] = (p, path.join(pkgroot, ldr, libname_full))
                break


def _resolve_dependencies(
    install_root: str, pkg: PkgCfg, pkgcfg: PkgCfgProvider, libs: LibsDict
):
    # first, gather all possible libraries by retrieving this package and
    # it's dependents. We're not concerned about redirecting non-robotpy-build
    # libraries, since we can't control where those are located
    deps = pkgcfg.get_all_deps(pkg.name)

    pypi_package = pkg.pypi_package

    for dep in deps:
        # dependencies are in their installed location
        # .. except when they're in the same wheel
        if pypi_package and dep.pypi_package == pypi_package:
            _resolve_libs_in_self(dep, install_root, libs)
        else:
            libdirs = dep.get_library_dirs()
            full_names = dep.get_library_full_names()
            if full_names:
                for libname_full in full_names:
                    _resolve_libs(libdirs, libname_full, libs)


def _fix_libs(to_fix: LibsDict, libs: LibsDict):

    for (current_libpath, install_libpath) in to_fix.values():
        for lib in get_install_names(current_libpath):
            libb = path.basename(lib)
            libdata = libs.get(libb)
            if libdata:
                desired_path = path.relpath(libdata[1], path.dirname(install_libpath))
                desired_path = "@loader_path/" + desired_path
                set_install_name(current_libpath, lib, desired_path)
            elif filter_system_libs(lib):
                raise ValueError(
                    "unresolved lib %s: maybe a dependency is missing?" % lib
                )


def relink_libs(install_root: str, pkg: PkgCfg, pkgcfg: PkgCfgProvider):
    """
    Given a package, relink it's external libraries

    :param install_root: Where this package will be (is) installed
    :param pkg: Object that implements pkgcfg for this wrapper
    :param pkgcfg: robotpy-build pkgcfg resolver
    """
    libs: LibsDict = {}
    _resolve_dependencies(install_root, pkg, pkgcfg, libs)
    to_fix: LibsDict = {}
    _resolve_libs_in_self(pkg, install_root, to_fix)
    libs.update(to_fix)
    _fix_libs(to_fix, libs)


def relink_extension(
    install_root: str,
    extension_path: str,
    extension_rel: str,
    pkg: PkgCfg,
    pkgcfg: PkgCfgProvider,
) -> LibsDict:
    """
    Given an extension, relink it

    :param install_root: Where this package will be (is) installed
    :param extension_path: full path to extension library
    :param extension_rel: Relative path to library where it will be (is) installed
    :param pkg: Object that implements pkgcfg for this wrapper
    :param pkgcfg: robotpy-build pkgcfg resolver
    """
    libs: LibsDict = {}
    _resolve_dependencies(install_root, pkg, pkgcfg, libs)
    _resolve_libs_in_self(pkg, install_root, libs)

    to_fix = {
        path.basename(extension_path): (
            extension_path,
            path.join(install_root, extension_rel),
        )
    }
    _fix_libs(to_fix, libs)
    return libs
