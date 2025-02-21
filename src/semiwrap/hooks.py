# TODO: rename this

import pathlib
import typing as T

from hatchling.plugin import hookimpl
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from .cmd_genmeson import gen_meson_to_file

from .config.pyproject_toml import SemiwrapHatchlingConfig


@hookimpl
def hatch_register_build_hook():
    return SemiwrapBuildHook


class SemiwrapBuildHook(BuildHookInterface):
    """
    Sets up code generation to be ran by meson
    """

    PLUGIN_NAME = "semiwrap"

    def initialize(self, version: str, build_data: T.Dict[str, T.Any]) -> None:
        # Only needed for building wheels
        if self.target_name != "wheel":
            return

        project_root = pathlib.Path(self.root)

        config = SemiwrapHatchlingConfig(**self.config)
        stage0_build_path = project_root / config.autogen_build_path
        stage0_meson_build = stage0_build_path / "meson.build"
        stage0_gitignore = stage0_build_path / ".gitignore"

        if config.module_build_path is not None:
            stage1_build_path = project_root / config.module_build_path
        else:
            stage1_build_path = stage0_build_path / "modules"

        stage1_meson_build = stage1_build_path / "meson.build"
        stage1_gitignore = stage1_build_path / ".gitignore"

        eps = gen_meson_to_file(project_root, stage0_meson_build, stage1_meson_build)

        if eps:
            # .. not documented but it works?
            for ep in eps:
                g = self.metadata.core.entry_points.setdefault(ep.group, {})
                g[ep.name] = ep.package

        if not stage0_gitignore.exists():
            stage0_gitignore.write_text("/meson.build\n")

        if not stage1_gitignore.exists():
            stage1_gitignore.write_text("/meson.build\n")
