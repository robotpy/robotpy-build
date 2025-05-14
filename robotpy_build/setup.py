import os
from os.path import abspath, exists, join
from setuptools import find_packages, setup as _setup
from setuptools_scm import get_version
import tomli

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel

    class bdist_wheel(_bdist_wheel):
        def finalize_options(self):
            _bdist_wheel.finalize_options(self)
            self.root_is_pure = False

except ImportError:
    bdist_wheel = None  # type: ignore

from .autowrap.writer import WrapperWriter

from .command.build_py import BuildPy
from .command.build_dl import BuildDl
from .command.build_gen import BuildGen
from .command.build_ext import BuildExt
from .command.build_pyi import BuildPyi
from .command.develop import Develop
from .command.update_init import UpdateInit

try:
    from .command.editable_wheel import EditableWheel
except ImportError:
    EditableWheel = None  # type: ignore

from .config.util import parse_input
from .config.pyproject_toml import RobotpyBuildConfig

from .maven import convert_maven_to_downloads
from .overrides import apply_overrides
from .pkgcfg_provider import PkgCfgProvider
from .platforms import get_platform, get_platform_override_keys
from .static_libs import StaticLib
from .wrapper import Wrapper


class Setup:
    """
    Hacky wrapper around setuptools because it's easier than copy/pasting
    this stuff to a million setup.py files
    """

    def __init__(self):
        self.root = abspath(os.getcwd())
        self.wrappers = []
        self.static_libs = []

        self.platform = get_platform()

        project_fname = join(self.root, "pyproject.toml")

        try:
            with open(project_fname, "rb") as fp:
                self.pyproject = tomli.load(fp)
        except FileNotFoundError as e:
            raise ValueError("current directory is not a robotpy-build project") from e

        self.project_dict = self.pyproject.get("tool", {}).get("robotpy-build", {})

        # Overrides are applied before processing, so that we can easily
        # override anything without needing to make the dataclasses messy
        # with needless details
        override_keys = get_platform_override_keys(self.platform)
        apply_overrides(self.project_dict, override_keys)

        try:
            self.project = parse_input(
                self.project_dict, RobotpyBuildConfig, project_fname
            )
        except Exception as e:
            raise ValueError(
                f"robotpy-build configuration in pyproject.toml is incorrect"
            ) from e

        # Shared wrapper writer instance
        self.wwriter = WrapperWriter()

    @property
    def base_package(self):
        return self.project.base_package

    @property
    def base_package_path(self):
        return join(self.root, *self.base_package.split("."))

    @property
    def git_dir(self):
        return join(self.root, ".git")

    @property
    def pypi_package(self) -> str:
        return self.setup_kwargs["name"]

    def prepare(self):
        self.setup_kwargs = self.project_dict.get("metadata", {})
        self.setup_kwargs["zip_safe"] = False
        self.setup_kwargs["include_package_data"] = True
        self.setup_kwargs["python_requires"] = ">=3.8"

        self._generate_long_description()

        # get_version expects the directory to exist
        base_package_path = self.base_package_path
        os.makedirs(base_package_path, exist_ok=True)
        this_version = get_version(
            write_to=join(base_package_path, "version.py"),
            fallback_version="master",
            search_parent_directories=True,
        )
        self.setup_kwargs["version"] = this_version

        # Support ==THIS_VERSION
        install_requires = self.setup_kwargs.get("install_requires")
        if install_requires:

            def _xform(v: str):
                if v.endswith("==THIS_VERSION"):
                    v = f"{v[:-14]}=={this_version}"
                return v

            self.setup_kwargs["install_requires"] = list(map(_xform, install_requires))

        self.pkgcfg = PkgCfgProvider()

        self._collect_static_libs()
        self._collect_wrappers()

        self.pkgcfg.detect_pkgs()

        self.setup_kwargs["cmdclass"] = {
            "build_py": BuildPy,
            "build_dl": BuildDl,
            "build_gen": BuildGen,
            "build_ext": BuildExt,
            "build_pyi": BuildPyi,
            "develop": Develop,
            "update_init": UpdateInit,
        }
        if EditableWheel:
            self.setup_kwargs["cmdclass"]["editable_wheel"] = EditableWheel
        if bdist_wheel:
            self.setup_kwargs["cmdclass"]["bdist_wheel"] = bdist_wheel
        for cls in self.setup_kwargs["cmdclass"].values():
            cls.wrappers = self.wrappers
            cls.static_libs = self.static_libs
            cls.rpybuild_pkgcfg = self.pkgcfg
        BuildPyi.base_package = self.base_package
        UpdateInit.update_list = self.project.update_init

        # We already know some of our packages, so collect those in addition
        # to using find_packages()
        packages = {w.package_name for w in self.wrappers}
        packages.update(find_packages())
        self.setup_kwargs["packages"] = list(packages)

    def _generate_long_description(self):
        readme_rst = join(self.root, "README.rst")
        readme_md = join(self.root, "README.md")
        if exists(readme_rst):
            self.setup_kwargs["long_description_content_type"] = "text/x-rst"
            with open(readme_rst) as fp:
                self.setup_kwargs["long_description"] = fp.read()

        elif exists(readme_md):
            self.setup_kwargs["long_description_content_type"] = "text/markdown"
            with open(readme_md) as fp:
                self.setup_kwargs["long_description"] = fp.read()

    def _collect_wrappers(self):
        ext_modules = []

        for package_name, cfg in self.project.wrappers.items():
            if cfg.ignore:
                continue
            self._fix_downloads(cfg, False)
            w = Wrapper(package_name, cfg, self, self.wwriter)
            self.wrappers.append(w)
            self.pkgcfg.add_pkg(w)

            if w.extension:
                ext_modules.append(w.extension)

        if ext_modules:
            self.setup_kwargs["ext_modules"] = ext_modules

    def _collect_static_libs(self):
        for name, cfg in self.project.static_libs.items():
            if cfg.ignore:
                continue
            self._fix_downloads(cfg, True)
            if not cfg.download:
                raise ValueError(f"static_lib {name} must specify downloads")
            s = StaticLib(name, cfg, self)
            self.static_libs.append(s)
            self.pkgcfg.add_pkg(s)

    def _fix_downloads(self, cfg, static: bool):
        # maven is just a special case of a download
        if cfg.maven_lib_download:
            downloads = convert_maven_to_downloads(cfg.maven_lib_download, static)
            cfg.maven_lib_download = None
            if cfg.download:
                cfg.download.append(downloads)
            else:
                cfg.download = downloads

        if cfg.download:
            for dl in cfg.download:
                dl._update_with_platform(self.platform)

    def run(self):
        # assemble all the pieces and make it work
        _setup(**self.setup_kwargs)


def setup():
    s = Setup()
    s.prepare()
    s.run()
