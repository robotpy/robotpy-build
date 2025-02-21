import pathlib
import typing as T

import tomli

from .config.pyproject_toml import ModuleConfig, SemiwrapToolConfig
from .overrides import apply_overrides
from .pkgconf_cache import PkgconfCache
from .platforms import get_platform, get_platform_override_keys


class PyProject:
    def __init__(self, pyproject_path: T.Optional[pathlib.Path] = None) -> None:

        if pyproject_path:
            self.root = pyproject_path.parent.resolve()
        else:
            self.root = pathlib.Path().resolve()

        self._pkgconf = None
        self._platform = None
        self._project = None

        self._all_deps = None

    @property
    def pkgconf(self):
        if self._pkgconf is None:
            self._pkgconf = PkgconfCache()
        return self._pkgconf

    @property
    def platform(self):
        if self._platform is None:
            self._platform = get_platform()
        return self._platform

    @property
    def project(self):
        if self._project is None:
            project_fname = self.root / "pyproject.toml"

            try:
                with open(project_fname, "rb") as fp:
                    self.pyproject = tomli.load(fp)
            except FileNotFoundError as e:
                raise ValueError("current directory is not a semiwrap project") from e

            self.project_dict = self.pyproject.get("tool", {}).get("semiwrap", {})

            # Overrides are applied before pydantic does processing, so that
            # we can easily override anything without needing to make the
            # pydantic schemas messy with needless details
            override_keys = get_platform_override_keys(self.platform)
            apply_overrides(self.project_dict, override_keys)

            try:
                self._project = SemiwrapToolConfig(**self.project_dict)
            except Exception as e:
                raise ValueError(
                    f"semiwrap configuration in pyproject.toml is incorrect"
                ) from e
        return self._project

    def get_module(self, package_name: str) -> ModuleConfig:
        return self.project.modules[package_name]

    def get_module_deps(self, module: ModuleConfig) -> T.List[str]:
        deps = []
        for wrap in module.wraps:
            if wrap not in module.depends:
                deps.append(wrap)
        deps.extend(module.depends)
        return deps
