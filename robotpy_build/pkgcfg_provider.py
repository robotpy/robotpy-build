import importlib.util
from os.path import join, dirname
from pkg_resources import iter_entry_points
import sys
from typing import Dict, List, Optional, Set
import warnings


def _hacky_entrypoint_loader(module_name):
    # load the root parent spec
    pkgs = module_name.split(".")
    spec = importlib.util.find_spec(pkgs[0])
    assert spec is not None and spec.origin is not None

    # even namespace packages are installed in the path, so just guess
    # ... and maybe it works?
    fname = join(dirname(spec.origin), *pkgs[1:]) + ".py"
    spec = importlib.util.spec_from_file_location(module_name, fname)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class PkgCfg:
    """
        Contains information about an installed package that uses robotpy-build
    """

    def __init__(self, entry_point):
        try:
            self.module = entry_point.load()
        except Exception as e:
            try:
                self.module = _hacky_entrypoint_loader(entry_point.module_name)
            except Exception:
                raise e

        self.name = entry_point.name

        # could deduce this, but this is probably fine
        self.libinit_import = getattr(self.module, "libinit_import", None)
        self.depends = getattr(self.module, "depends", [])
        self.pypi_package = getattr(self.module, "pypi_package", None)
        self.package_name = getattr(self.module, "package_name", None)
        self.static_lib = getattr(self.module, "static_lib", False)

    def get_include_dirs(self) -> Optional[List[str]]:
        """
            Include directories provided by this module
        """
        fn = getattr(self.module, "get_include_dirs", None)
        if fn:
            return fn()
        return None

    def get_library_dirs(self) -> Optional[List[str]]:
        """
            Directories where libraries reside
        """
        fn = getattr(self.module, "get_library_dirs", None)
        if fn:
            return fn()
        return None

    def get_library_dirs_rel(self) -> Optional[List[str]]:
        """
            Directories where libraries reside, relative to package
        """
        fn = getattr(self.module, "get_library_dirs_rel", None)
        if fn:
            return fn()
        return None

    def get_library_names(self) -> Optional[List[str]]:
        """
            Names of libraries provided (for linking)
        """
        fn = getattr(self.module, "get_library_names", None)
        if fn:
            return fn()
        return None

    def get_extra_objects(self) -> Optional[List[str]]:
        """
            Names of extra objects to link in
        """
        fn = getattr(self.module, "get_extra_objects", None)
        if fn:
            return fn()
        return None

    def get_library_full_names(self) -> Optional[List[str]]:
        """
            Full names of libraries provided (needed for OSX support)
        """
        fn = getattr(self.module, "get_library_full_names", None)
        if fn:
            return fn()
        return None

    def get_type_casters(self, casters: Dict[str, str]) -> None:
        """
            Type caster headers provided
        """
        fn = getattr(self.module, "get_type_casters", None)
        if fn:
            return fn(casters)


class PkgCfgProvider:
    """
        Retrieves information about robotpy-build packages

        Warning: Not to be confused with 'pkg-config'
    """

    def __init__(self):
        self.pkgs = {}
        for entry_point in iter_entry_points(group="robotpybuild", name=None):
            try:
                pkg = PkgCfg(entry_point)
            except Exception as e:
                warnings.warn(f"Error loading entry point {entry_point.name}: {e}")
            else:
                self.add_pkg(pkg)

    def add_pkg(self, pkg: PkgCfg) -> None:
        self.pkgs[pkg.name] = pkg

    def get_pkg(self, name: str) -> PkgCfg:
        try:
            return self.pkgs[name]
        except KeyError:
            raise KeyError("robotpy-build package '%s' not installed" % name)

    def get_all_deps(self, name: str) -> Set[PkgCfg]:
        deps: Set[PkgCfg] = set()

        def _get(name: str):
            pkg = self.get_pkg(name)
            if pkg in deps:
                return pkg
            deps.add(pkg)
            for dep in pkg.depends:
                _get(dep)
            return pkg

        pkg = _get(name)
        deps.remove(pkg)
        return deps
