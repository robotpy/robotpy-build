from pkg_resources import iter_entry_points
from typing import Dict, List, Optional, Set
import warnings


class PkgCfg:
    """
        Contains information about an installed package that uses robotpy-build
    """

    def __init__(self, entry_point):
        self.module = entry_point.load()
        self.name = entry_point.name

        # could deduce this, but this is probably fine
        self.import_name = getattr(self.module, "import_name", None)
        self.depends = getattr(self.module, "depends", [])

    def get_include_dirs(self) -> Optional[List[str]]:
        """
            Include directories provided by this module
        """
        fn = getattr(self.module, "get_include_dirs", None)
        if fn:
            return fn()

    def get_library_dirs(self) -> Optional[List[str]]:
        """
            Directories where libraries reside
        """
        fn = getattr(self.module, "get_library_dirs", None)
        if fn:
            return fn()

    def get_library_names(self) -> Optional[List[str]]:
        """
            Names of libraries provided
        """
        fn = getattr(self.module, "get_library_names", None)
        if fn:
            return fn()


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

    def get_pkg(self, name: str) -> str:
        try:
            return self.pkgs[name]
        except KeyError:
            raise KeyError("robotpy-build package '%s' not installed" % name)

    def get_all_deps(self, name: str) -> Set[PkgCfg]:
        deps = set()

        def _get(name: str):
            pkg = self.get_pkg(name)
            for dep in pkg.depends:
                if dep not in deps:
                    deps.add(_get(dep))
            return pkg

        _get(name)
        return deps
