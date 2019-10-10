from pkg_resources import iter_entry_points
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

    def get_include_dirs(self):
        fn = getattr(self.module, "get_include_dirs", None)
        if fn:
            return fn()

    def get_library_dirs(self):
        fn = getattr(self.module, "get_library_dirs", None)
        if fn:
            return fn()

    def get_library_names(self):
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

    def add_pkg(self, pkg):
        self.pkgs[pkg.name] = pkg

    def get_pkg(self, name):
        try:
            return self.pkgs[name]
        except KeyError:
            raise KeyError("robotpy-build package '%s' not installed" % name)

