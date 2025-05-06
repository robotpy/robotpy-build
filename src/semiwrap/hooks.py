# TODO: rename this

import os
import pathlib
import sys
import traceback
import typing as T

from hatchling.plugin import hookimpl
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from .render_meson import render_meson_to_file

from .config.pyproject_toml import SemiwrapHatchlingConfig
from .config.util import parse_input


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

        project_root = pathlib.Path(self.root).resolve()

        config = parse_input(
            self.config, SemiwrapHatchlingConfig, "[tool.hatch.build.hooks.semiwrap]"
        )
        stage0_build_path = project_root / config.autogen_build_path
        stage0_meson_build = stage0_build_path / "meson.build"
        stage0_gitignore = stage0_build_path / ".gitignore"

        if config.module_build_path is not None:
            stage1_build_path = project_root / config.module_build_path
        else:
            stage1_build_path = stage0_build_path / "modules"

        stage1_meson_build = stage1_build_path / "meson.build"

        # This is used to generate files installed into a directory called 'trampolines'
        # so due to https://github.com/mesonbuild/meson/issues/2320 this must also be
        # in a directory called 'trampolines'
        # - unlike stage0 and stage1, this is included by stage0
        trampoline_build_path = stage0_build_path / "trampolines"
        trampoline_meson_build = trampoline_build_path / "meson.build"

        try:
            eps = render_meson_to_file(
                project_root,
                stage0_meson_build,
                stage1_meson_build,
                trampoline_meson_build,
            )
        except Exception as e:
            # Reading the stack trace is annoying, most of the time the exception content
            # is enough to figure out what you did wrong.
            if os.environ.get("SEMIWRAP_ERROR_VERBOSE") == "1":
                raise

            msg = [
                "ERROR: exception occurred when processing `pyproject.toml`\n\n",
            ]

            msg += traceback.format_exception_only(type(e), e)
            cause = e.__context__
            while cause is not None:
                if "prepare_metadata_for_build_editable" in str(cause):
                    break

                el = traceback.format_exception_only(type(cause), cause)
                el[0] = f"- caused by {el[0]}"
                msg += el

                if cause.__suppress_context__:
                    break

                cause = cause.__context__

            msg.append(
                "\nSet environment variable SEMIWRAP_ERROR_VERBOSE=1 for stacktrace"
            )

            print("".join(msg), file=sys.stderr)
            sys.exit(1)

        if eps:
            # .. not documented but it works?
            for ep in eps:
                g = self.metadata.core.entry_points.setdefault(ep.group, {})
                g[ep.name] = ep.package

        if not stage0_gitignore.exists():
            stage0_gitignore.write_text(
                "/meson.build\n"
                f"/{stage1_build_path.name}/meson.build\n"
                f"/{trampoline_build_path.name}/meson.build\n"
            )
