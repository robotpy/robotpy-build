import pathlib
import typing as T

import packaging.markers
import tomli

from .config.util import parse_input
from .config.pyproject_toml import ExtensionModuleConfig, SemiwrapToolConfig


class PyProject:
    def __init__(self, pyproject_path: T.Optional[pathlib.Path] = None) -> None:

        if pyproject_path:
            self.root = pyproject_path.parent.resolve()
        else:
            self.root = pathlib.Path().resolve()

        self._platform = None
        self._project = None
        self._package_root = None

        self._all_deps = None

        self._evaluated_markers: T.Dict[str, bool] = {}

    def _enable_if(self, condition: str) -> bool:
        """
        Evaluates a string containing PEP 508 environment markers
        """
        ok = self._evaluated_markers.get(condition)
        if ok is None:
            ok = packaging.markers.Marker(condition).evaluate()
            self._evaluated_markers[condition] = ok

        return ok

    @property
    def package_root(self) -> pathlib.Path:
        if self._package_root is None:
            # try to detect packages based on the extension modules
            for package_name in self.project.extension_modules.keys():
                parent = pathlib.Path(*package_name.split(".")[:-1])
                if (self.root / parent / "__init__.py").exists():
                    self._package_root = self.root
                    break
                elif (self.root / "src" / parent / "__init__.py").exists():
                    self._package_root = self.root / "src"
                    break
            else:
                raise ValueError("Cannot determine package root")

        return self._package_root

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

            try:
                self._project = parse_input(
                    self.project_dict, SemiwrapToolConfig, project_fname
                )
            except Exception as e:
                raise ValueError(
                    f"semiwrap configuration in pyproject.toml is incorrect"
                ) from e
        return self._project

    def get_extension(self, module_package_name: str) -> ExtensionModuleConfig:
        return self.project.extension_modules[module_package_name]

    def get_extension_deps(self, extension: ExtensionModuleConfig) -> T.List[str]:
        deps = []
        for wrap in extension.wraps:
            if wrap not in extension.depends:
                deps.append(wrap)
        deps.extend(extension.depends)
        return deps

    def get_extension_headers(
        self, extension: ExtensionModuleConfig
    ) -> T.Generator[T.Tuple[str, str], None, None]:
        for yml, hdr in extension.headers.items():
            if isinstance(hdr, str):
                yield yml, hdr
            elif self._enable_if(hdr.enable_if):
                yield yml, hdr.header
