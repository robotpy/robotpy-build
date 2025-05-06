from __future__ import annotations

import collections
import dataclasses
import os
import pathlib
import pprint
import sys
import sysconfig
import typing as T

from .casters import PKGCONF_CASTER_EXT
from .config.autowrap_yml import AutowrapConfigYaml
from .config.pyproject_toml import ExtensionModuleConfig, TypeCasterConfig
from .pkgconf_cache import PkgconfCache
from .pyproject import PyProject
from .util import relpath_walk_up

import toposort


@dataclasses.dataclass
class Entrypoint:
    """
    Represents a python entrypoint that needs to be created when the wheel is installed

    .. seealso:: https://packaging.python.org/en/latest/specifications/entry-points/
    """

    name: str
    group: str
    package: str


@dataclasses.dataclass(frozen=True)
class CppMacroValue:
    """
    Represents the value of a macro defined by the C++ compiler
    """

    name: str


@dataclasses.dataclass(frozen=True)
class LocalDependency:
    name: str
    include_paths: T.Tuple[pathlib.Path, ...]
    depends: T.Tuple[T.Union[LocalDependency, str], ...]


@dataclasses.dataclass(frozen=True)
class InputFile:
    # TODO: what is this relative to?
    path: pathlib.Path


@dataclasses.dataclass(frozen=True)
class OutputFile:
    name: str


@dataclasses.dataclass(frozen=True)
class Depfile:
    # this is needed anytime a command generates something based on something
    # that is more than just the input file
    name: str


@dataclasses.dataclass(frozen=True)
class BuildTargetOutput:
    # references a specific build target output
    target: BuildTarget
    output_index: int


@dataclasses.dataclass(frozen=True)
class BuildTarget:
    command: str

    args: T.Tuple[
        T.Union[
            str,
            pathlib.Path,
            InputFile,
            OutputFile,
            Depfile,
            BuildTarget,
            BuildTargetOutput,
            CppMacroValue,
        ],
        ...,
    ]

    # Install path is always relative to py.get_install_dir(pure: false)
    install_path: T.Optional[pathlib.Path]


@dataclasses.dataclass(frozen=True)
class ExtensionModule:

    #: variable name/prefix in the build file
    name: str

    #: full package name of installed extension
    package_name: str

    sources: T.Tuple[BuildTarget, ...]
    depends: T.Tuple[T.Union[LocalDependency, str], ...]

    # extra include directories that won't be found via depends
    include_directories: T.Tuple[pathlib.Path, ...]

    # Install path is always relative to py.get_install_dir(pure: false)
    install_path: pathlib.Path


class PlanError(Exception):
    pass


def _split_ns(name: str) -> T.Tuple[str, str]:
    ns = ""
    idx = name.rfind("::")
    if idx != -1:
        ns = name[:idx]
        name = name[idx + 2 :]
    return ns, name


class _BuildPlanner:
    def __init__(self, project_root: pathlib.Path, missing_yaml_ok: bool = False):

        self.project_root = project_root
        self.missing_yaml_ok = missing_yaml_ok

        self.pyproject = PyProject(project_root / "pyproject.toml")
        self.pkgcache = PkgconfCache()
        self.pyproject_input = InputFile(project_root / "pyproject.toml")

        self.pyi_targets: T.List[BuildTarget] = []
        self.pyi_args = []

        self.local_caster_targets: T.Dict[str, BuildTargetOutput] = {}
        self.local_dependencies: T.Dict[str, LocalDependency] = {}

        sw_path = self.pkgcache.get("semiwrap").type_casters_path
        assert sw_path is not None
        self.semiwrap_type_caster_path = sw_path

    def generate(self):

        projectcfg = self.pyproject.project

        #
        # Export type casters
        # .. this probably should be its own hatchling plugin?
        #

        for name, caster_cfg in projectcfg.export_type_casters.items():
            yield from self._process_export_type_caster(name, caster_cfg)

        # This is needed elsewhere
        self._cpp_macro = CppMacroValue("__cplusplus")
        yield self._cpp_macro

        #
        # Generate extension modules
        #

        for package_name, extension in self._sorted_extension_modules():
            try:
                yield from self._process_extension_module(package_name, extension)
            except Exception as e:
                raise PlanError(f"{package_name} failed") from e

        # TODO: this conditional probably should be done in the build system instead
        # cannot build pyi files when cross-compiling
        if not (
            "_PYTHON_HOST_PLATFORM" in os.environ
            or "PYTHON_CROSSENV" in os.environ
            or os.environ.get("SEMIWRAP_SKIP_PYI") == "1"
        ):
            # Make a pyi for every module
            # - they depend on every module because it needs a working environment
            #   and the user might import something
            # - if there's a subpkg this fails, need to think about it
            for pyi_target in self.pyi_targets:
                yield BuildTarget(
                    command="make-pyi",
                    args=pyi_target.args + tuple(self.pyi_args),
                    install_path=pyi_target.install_path,
                )

    def _resolve_dep(self, dname: str):
        return self.local_dependencies.get(dname, dname)

    def _process_export_type_caster(self, name: str, caster_cfg: TypeCasterConfig):

        # Need to generate the data file and the .pc file
        caster_target = BuildTarget(
            command="publish-casters",
            args=(
                self.pyproject_input,
                name,
                OutputFile(f"{name}{PKGCONF_CASTER_EXT}"),
                OutputFile(f"{name}.pc"),
            ),
            install_path=pathlib.Path(*caster_cfg.pypackage.split(".")),
        )
        yield caster_target

        # Need an entrypoint to point at the .pc file
        yield Entrypoint(group="pkg_config", name=name, package=caster_cfg.pypackage)

        dep = self.pkgcache.add_local(
            name=name,
            includes=[self.project_root / inc for inc in caster_cfg.includedir],
            requires=caster_cfg.requires,
        )
        caster_dep = LocalDependency(
            name=dep.name,
            include_paths=tuple(dep.include_path),
            depends=tuple([self._resolve_dep(cd) for cd in caster_cfg.requires]),
        )
        self.local_dependencies[dep.name] = caster_dep
        yield caster_dep

        # The .pc file cannot be used in the build, but the data file must be, so
        # store it so it can be used elsewhere
        self.local_caster_targets[name] = BuildTargetOutput(caster_target, 0)

    def _sorted_extension_modules(
        self,
    ) -> T.Generator[T.Tuple[str, ExtensionModuleConfig], None, None]:
        # sort extension modules by dependencies, that way modules can depend on other modules
        # also declared in pyproject.toml without needing to worry about ordering in the file
        by_name = {}
        to_sort: T.Dict[str, T.Set[str]] = {}

        for package_name, extension in self.pyproject.project.extension_modules.items():
            if extension.ignore:
                continue

            name = extension.name or package_name.replace(".", "_")
            by_name[name] = (package_name, extension)

            deps = to_sort.setdefault(name, set())
            for dep in extension.wraps:
                deps.add(dep)
            for dep in extension.depends:
                deps.add(dep)

        for name in toposort.toposort_flatten(to_sort, sort=True):
            data = by_name.get(name)
            if data:
                yield data

    def _process_extension_module(
        self, package_name: str, extension: ExtensionModuleConfig
    ):
        package_path_elems = package_name.split(".")
        parent_package = ".".join(package_path_elems[:-1])
        module_name = package_path_elems[-1]
        package_path = pathlib.Path(*package_path_elems[:-1])
        varname = extension.name or package_name.replace(".", "_")

        # Detect the location of the package in the source tree
        package_init_py = self.pyproject.package_root / package_path / "__init__.py"
        self.pyi_args += [parent_package, package_init_py.as_posix()]

        depends = self.pyproject.get_extension_deps(extension)
        depends.append("semiwrap")

        # Search path for wrapping is dictated by package_path and wraps
        search_path, include_directories_uniq, caster_json_file, libinit_modules = (
            self._prepare_dependency_paths(depends, extension)
        )

        includes = [
            self.project_root / pathlib.PurePosixPath(inc) for inc in extension.includes
        ]
        search_path.extend(includes)

        # Search the package path last
        search_path.append(self.pyproject.package_root / package_path)

        all_type_casters = BuildTarget(
            command="resolve-casters",
            args=(
                OutputFile(f"{varname}.casters.pkl"),
                Depfile(f"{varname}.casters.d"),
                *caster_json_file,
            ),
            install_path=None,
        )
        yield all_type_casters

        #
        # Generate init.py for loading dependencies
        #

        libinit_module = None
        if libinit_modules:
            libinit_py = extension.libinit or f"_init_{module_name}.py"
            libinit_tgt = BuildTarget(
                command="gen-libinit-py",
                args=(OutputFile(libinit_py), *libinit_modules),
                install_path=package_path,
            )

            libinit_module = f"{parent_package}.{libinit_py}"[:-3]
            self.pyi_args += [libinit_module, libinit_tgt]

            yield libinit_tgt

        #
        # Publish a .pc file for this module
        #

        pc_args = [
            package_name,
            varname,
            self.pyproject_input,
            OutputFile(f"{varname}.pc"),
        ]
        if libinit_module:
            pc_args += ["--libinit-py", libinit_module]

        yield BuildTarget(
            command="gen-pkgconf",
            args=tuple(pc_args),
            install_path=package_path,
        )

        yield Entrypoint(group="pkg_config", name=varname, package=parent_package)

        #
        # Process the headers
        #

        # Find and load the yaml
        if extension.yaml_path is None:
            yaml_path = pathlib.Path("semiwrap")
        else:
            yaml_path = pathlib.Path(pathlib.PurePosixPath(extension.yaml_path))

        datfiles, module_sources, subpackages = yield from self._process_headers(
            extension,
            package_path,
            yaml_path,
            include_directories_uniq.keys(),
            search_path,
            all_type_casters,
        )

        modinit = BuildTarget(
            command="gen-modinit-hpp",
            args=(
                module_name,
                OutputFile(f"semiwrap_init.{package_name}.hpp"),
                *datfiles,
            ),
            install_path=None,
        )
        module_sources.append(modinit)
        yield modinit

        #
        # Emit the module
        #

        # Use a local dependency to store everything so it can be referenced elsewhere
        cached_dep = self.pkgcache.add_local(
            name=varname,
            includes=[*includes, self.pyproject.package_root / package_path],
            requires=depends,
            libinit_py=libinit_module,
        )
        local_dep = LocalDependency(
            name=cached_dep.name,
            include_paths=tuple(cached_dep.include_path),
            depends=tuple(self._resolve_dep(dep) for dep in depends),
        )
        yield local_dep
        self.local_dependencies[local_dep.name] = local_dep

        modobj = ExtensionModule(
            name=varname,
            package_name=package_name,
            sources=tuple(module_sources),
            depends=(local_dep,),
            include_directories=tuple(),
            install_path=package_path,
        )
        yield modobj

        self.pyi_args += [package_name, modobj]

        # This is not yielded here because pyi targets need to depend on all modules
        # via self.pyi_args.
        # - The output .pyi files vary based on whether there are subpackages or not. If no
        #   subpackage, it's {module_name}.pyi. If there are subpackages, it becomes
        #   {module_name}/__init__.pyi and {module_name}/{subpackage}.pyi
        # - As long as a user doesn't manually bind a subpackage our detection works here
        #   but if we need to allow that then will need to declare subpackages in pyproject.toml
        # .. this breaks if there are sub-sub packages, don't do that please

        base_pyi_elems = package_name.split(".")

        if subpackages:
            pyi_elems = base_pyi_elems + ["__init__.pyi"]
            pyi_args = [
                pathlib.PurePath(*pyi_elems).as_posix(),
                OutputFile("__init__.pyi"),
            ]
            for subpackage in subpackages:
                pyi_elems = base_pyi_elems + [f"{subpackage}.pyi"]
                pyi_args += [
                    pathlib.PurePath(*pyi_elems).as_posix(),
                    OutputFile(f"{subpackage}.pyi"),
                ]

            self.pyi_targets.append(
                BuildTarget(
                    command="make-pyi",
                    args=(package_name, *pyi_args, "--"),
                    install_path=package_path / module_name,
                )
            )

        else:
            base_pyi_elems[-1] = f"{base_pyi_elems[-1]}.pyi"

            self.pyi_targets.append(
                BuildTarget(
                    command="make-pyi",
                    args=(
                        package_name,
                        pathlib.PurePath(*base_pyi_elems).as_posix(),
                        OutputFile(f"{module_name}.pyi"),
                        "--",
                    ),
                    install_path=package_path,
                )
            )

    def _locate_type_caster_json(
        self,
        depname: str,
        caster_json_file: T.List[T.Union[BuildTargetOutput, pathlib.Path]],
    ):
        checked = set()
        to_check = collections.deque([depname])
        while to_check:
            name = to_check.popleft()
            checked.add(name)

            entry = self.pkgcache.get(name)

            if name in self.local_caster_targets:
                caster_json_file.append(self.local_caster_targets[name])
            else:
                tc = entry.type_casters_path
                if tc and tc not in caster_json_file:
                    caster_json_file.append(tc)

            for req in entry.requires:
                if req not in checked:
                    to_check.append(req)

    def _prepare_dependency_paths(
        self, depends: T.List[str], extension: ExtensionModuleConfig
    ):
        search_path: T.List[pathlib.Path] = []
        include_directories_uniq: T.Dict[pathlib.Path, bool] = {}
        caster_json_file: T.List[T.Union[BuildTargetOutput, pathlib.Path]] = []
        libinit_modules: T.List[str] = []

        # Add semiwrap default type casters
        caster_json_file.append(self.semiwrap_type_caster_path)

        for dep in depends:
            entry = self.pkgcache.get(dep)
            include_directories_uniq.update(
                dict.fromkeys(entry.full_include_path, True)
            )

            # extend the search path if the dependency is in 'wraps'
            if dep in extension.wraps:
                search_path.extend(entry.include_path)

            self._locate_type_caster_json(dep, caster_json_file)

            if entry.libinit_py:
                libinit_modules.append(entry.libinit_py)

        return search_path, include_directories_uniq, caster_json_file, libinit_modules

    def _process_headers(
        self,
        extension: ExtensionModuleConfig,
        package_path: pathlib.Path,
        yaml_path: pathlib.Path,
        include_directories_uniq: T.Iterable[pathlib.Path],
        search_path: T.List[pathlib.Path],
        all_type_casters: BuildTarget,
    ):
        datfiles: T.List[BuildTarget] = []
        module_sources: T.List[BuildTarget] = []
        subpackages: T.Set[str] = set()

        for yml, hdr in self.pyproject.get_extension_headers(extension):
            yml_input = InputFile(yaml_path / f"{yml}.yml")

            try:
                ayml = AutowrapConfigYaml.from_file(self.project_root / yml_input.path)
            except FileNotFoundError:
                if not self.missing_yaml_ok:
                    msg = f"{self.project_root / yml_input.path}: use `python3 -m semiwrap create-yaml --write` to generate"
                    raise FileNotFoundError(msg) from None
                ayml = AutowrapConfigYaml()

            # find the source header
            h_input, h_root = self._locate_header(hdr, search_path)

            header2dat_args = []
            for inc in include_directories_uniq:
                header2dat_args += ["-I", inc]

            # https://github.com/pkgconf/pkgconf/issues/391
            header2dat_args += ["-I", sysconfig.get_path("include")]

            header2dat_args += ["--cpp", self._cpp_macro]

            header2dat_args.append(yml)
            header2dat_args.append(yml_input)
            header2dat_args.append(h_input)
            header2dat_args.append(h_root)
            header2dat_args.append(all_type_casters)
            header2dat_args.append(OutputFile(f"{yml}.dat"))
            header2dat_args.append(Depfile(f"{yml}.d"))

            datfile = BuildTarget(
                command="header2dat", args=tuple(header2dat_args), install_path=None
            )
            yield datfile
            datfiles.append(datfile)

            # Every header has a .cpp file for binding
            cppfile = BuildTarget(
                command="dat2cpp",
                args=(datfile, OutputFile(f"{yml}.cpp")),
                install_path=None,
            )
            module_sources.append(cppfile)
            yield cppfile

            # Detect subpackages
            for f in ayml.functions.values():
                if f.ignore:
                    continue
                if f.subpackage:
                    subpackages.add(f.subpackage)
                for f in f.overloads.values():
                    if f.subpackage:
                        subpackages.add(f.subpackage)

            for e in ayml.enums.values():
                if e.ignore:
                    continue
                if e.subpackage:
                    subpackages.add(e.subpackage)

            # Every class gets a trampoline file, but some just have #error in them
            for name, ctx in ayml.classes.items():
                if ctx.ignore:
                    continue

                if ctx.subpackage:
                    subpackages.add(ctx.subpackage)

                cls_ns, cls_name = _split_ns(name)
                cls_ns = cls_ns.replace(":", "_")
                trampoline = BuildTarget(
                    command="dat2trampoline",
                    args=(datfile, name, OutputFile(f"{cls_ns}__{cls_name}.hpp")),
                    install_path=package_path / "trampolines",
                )
                module_sources.append(trampoline)
                yield trampoline

            # Even more files if there are templates
            if ayml.templates:

                # Every template instantiation gets a cpp file to lessen compiler
                # memory requirements
                for i, (name, tctx) in enumerate(ayml.templates.items(), start=1):
                    if tctx.subpackage:
                        subpackages.add(tctx.subpackage)

                    tmpl_cpp = BuildTarget(
                        command="dat2tmplcpp",
                        args=(datfile, name, OutputFile(f"{yml}_tmpl{i}.cpp")),
                        install_path=None,
                    )
                    module_sources.append(tmpl_cpp)
                    yield tmpl_cpp

                # All of which use this hpp file
                tmpl_hpp = BuildTarget(
                    command="dat2tmplhpp",
                    args=(datfile, OutputFile(f"{yml}_tmpl.hpp")),
                    install_path=None,
                )
                module_sources.append(tmpl_hpp)
                yield tmpl_hpp

        return datfiles, module_sources, subpackages

    def _locate_header(self, hdr: str, search_path: T.List[pathlib.Path]):
        phdr = pathlib.PurePosixPath(hdr)
        for p in search_path:
            h_path = p / phdr
            if h_path.exists():
                # We should return this as an InputFile, but inputs must be relative to the
                # project root, which may not be the case on windows. Incremental build should
                # still work, because the header is included in a depfile
                return h_path, p
        raise FileNotFoundError(
            f"cannot locate {phdr} in {', '.join(map(str, search_path))}"
        )


def makeplan(project_root: pathlib.Path, missing_yaml_ok: bool = False) -> T.Generator[
    T.Union[BuildTarget, Entrypoint, LocalDependency, ExtensionModule, CppMacroValue],
    None,
]:
    """
    Given the pyproject.toml configuration for a semiwrap project, reads the
    configuration and generates a series of commands that can be used to parse
    the input headers and generate the needed source code from them.
    """
    planner = _BuildPlanner(project_root, missing_yaml_ok)
    yield from planner.generate()


def main():
    # this command only exists for debugging purposes
    try:
        _, project_root = sys.argv
    except ValueError:
        print(f"{sys.argv[0]} project_root", file=sys.stderr)
        sys.exit(1)

    output = list(makeplan(pathlib.Path(project_root)))
    pprint.pprint(output, indent=1)


if __name__ == "__main__":
    main()
