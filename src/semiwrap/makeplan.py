from __future__ import annotations

import dataclasses
import pathlib
import pprint
import sys
import typing as T

from .casters import PKGCONF_CASTER_EXT
from .config.autowrap_yml import AutowrapConfigYaml
from .pkgconf_cache import PkgconfCache
from .pyproject import PyProject


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
class BuildTarget:
    command: str

    args: T.Tuple[
        T.Union[str, pathlib.Path, InputFile, OutputFile, Depfile, BuildTarget], ...
    ]

    # Install path is always relative to py.get_install_dir(pure: false)
    install_path: T.Optional[pathlib.Path]


@dataclasses.dataclass(frozen=True)
class Module:
    name: str

    sources: T.Tuple[BuildTarget]
    depends: T.Tuple[str, ...]

    # Install path is always relative to py.get_install_dir(pure: false)
    install_path: pathlib.Path

    package_name: str


def _split_ns(name: str) -> T.Tuple[str, str]:
    ns = ""
    idx = name.rfind("::")
    if idx != -1:
        ns = name[:idx]
        name = name[idx + 2 :]
    return ns, name


def makeplan(project_root: pathlib.Path, missing_yaml_ok: bool = False):
    """
    Given the pyproject.toml configuration for a semiwrap project, reads the
    configuration and generates a list of commands that can be used to parse
    the input headers and generate the needed source code from them.

    All paths generated are relative to the project_root or absolute?
    """

    pkgcache = PkgconfCache()

    pyproject = PyProject(project_root / "pyproject.toml")
    projectcfg = pyproject.project

    pyproject_input = InputFile(project_root / "pyproject.toml")

    pyi_targets: T.List[BuildTarget] = []
    pyi_args = []

    for package_name, module in projectcfg.modules.items():
        if module.ignore:
            continue

        package_path = pathlib.Path(*package_name.split("."))

        package_init_py = project_root / package_path / "__init__.py"
        if not package_init_py.exists():
            package_init_py = project_root / "src" / package_path / "__init__.py"

        if package_init_py.exists():
            pyi_args += (package_name, str(package_init_py))
        else:
            # For now, we only support either src layout or flat layout
            raise FileNotFoundError(f"cannot find {package_name} module")

        if module.libinit:
            libinit_py = module.libinit
        else:
            libinit_py = f"_init_{module.name}.py"

        # This is only needed if the module has shared library dependencies
        # that must be loaded
        libinit_target = None
        if module.depends or module.wraps:
            libinit_target = BuildTarget(
                command="gen-libinit-py",
                args=(pyproject_input, package_name, OutputFile(libinit_py)),
                install_path=package_path,
            )
            yield libinit_target

        # TODO: probably should generate this via build system? how would we add the
        #       pc var there then? .. or maybe this tells hatch-mkpkgconf to do it
        if False:
            # this probably should be if module_type_casters or shared library?
            yield Entrypoint(group="pkg_config", name=module.name, package=package_name)

            # this only is needed when something is linking to this module, which
            # means it cannot be a python extension?
            # .. this probably isn't a semiwrap thing, it's on the user?
            # .. or were we going to use the pc to find the casters? but even
            #    then, those are only applicable to shared libraries
            # .. yeah, we need this to find the casters
            yield BuildTarget(
                command="make-pc",
                args=[pyproject_input, package_name, OutputFile(f"{name}.pc")],
                install_path=package_path,
            )

        if module.type_casters:
            yield Entrypoint(group="pkg_config", name=module.name, package=package_name)

            # cmd, pyproject, modname, name.pybind11.json, out=json, in=pyproject
            # .. this output must be published to pkgconf
            yield BuildTarget(
                command="publish-casters",
                args=(
                    pyproject_input,
                    package_name,
                    OutputFile(f"{module.name}{PKGCONF_CASTER_EXT}"),
                    OutputFile(f"{module.name}.pc"),
                ),
                install_path=package_path,
            )

        depends = pyproject.get_module_deps(module)
        depends.append("semiwrap")

        search_path: T.List[pathlib.Path] = []
        include_directories_uniq = {}

        for dep in depends:
            entry = pkgcache.get(dep)
            include_directories_uniq.update(
                dict.fromkeys(entry.full_include_path, True)
            )
            search_path.extend(entry.include_path)

        search_path.append(project_root)

        all_type_casters = BuildTarget(
            command="resolve-casters",
            args=(
                pyproject_input,
                package_name,
                OutputFile(f"{module.name}.casters.pkl"),
                Depfile(f"{module.name}.casters.d"),
            ),
            install_path=None,
        )
        yield all_type_casters

        # Find and load the yaml
        if module.yaml_path is None:
            yaml_path = pathlib.Path("wrapcfg")
        else:
            yaml_path = pathlib.Path(pathlib.PurePosixPath(module.yaml_path))

        datfiles: T.List[BuildTarget] = []
        module_sources = []

        for yml, hdr in module.headers.items():

            yml_input = InputFile(yaml_path / f"{yml}.yml")

            try:
                ayml = AutowrapConfigYaml.from_file(project_root / yml_input.path)
            except FileNotFoundError:
                if not missing_yaml_ok:
                    raise
                ayml = AutowrapConfigYaml()

            # find the source header
            # - TODO: this can be outside the project
            for p in search_path:
                h_path = p / hdr
                if h_path.exists():
                    h_input = InputFile(h_path.relative_to(project_root))
                    break
            else:
                raise FileNotFoundError(
                    f"cannot locate {hdr} in {', '.join(map(str, search_path))}"
                )

            header2dat_args = []
            for inc in include_directories_uniq.keys():
                header2dat_args += ["-I", inc]

            header2dat_args.append(module.name)
            header2dat_args.append(yml_input)
            header2dat_args.append(h_input)
            header2dat_args.append(all_type_casters)
            header2dat_args.append(OutputFile(f"{yml}.dat"))
            header2dat_args.append(Depfile(f"{yml}.d"))

            datfile = BuildTarget(
                command="header2dat",
                args=tuple(header2dat_args),
                install_path=None,
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

            # Every class gets a trampoline file, but some just have #error in them
            # .. hm, this means the yml needs to have the class namespace in it now
            #    .. which is probably a good thing, but will be annoying to migrate
            for name, _ in ayml.classes.items():
                cls_ns, cls_name = _split_ns(name)

                trampoline = BuildTarget(
                    command="dat2trampoline",
                    args=(datfile, name, OutputFile(f"{cls_ns}__{cls_name}.hpp")),
                    install_path=package_path / "rpy-include",
                )
                module_sources.append(trampoline)
                yield trampoline

            # Even more files if there are templates
            if ayml.templates:
                # Every template instantiation gets a cpp file to lessen compiler
                # memory requirements
                for i, (name, _) in enumerate(ayml.templates.items(), start=1):
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

        modinit = BuildTarget(
            command="gen-modinit-hpp",
            args=(module.name, OutputFile("autogen_module_init.hpp"), *datfiles),
            install_path=None,
        )
        module_sources.append(modinit)
        yield modinit

        modobj = Module(
            name=module.name,
            sources=tuple(module_sources),
            depends=tuple(depends),
            install_path=package_path,
            package_name=package_name,
        )
        yield modobj

        if libinit_target is not None:
            pyi_args += [libinit_py, libinit_target]

        full_module_name = f"{package_name}._{modobj.name}"
        pyi_args += [full_module_name, modobj]

        pyi_targets.append(
            BuildTarget(
                command="make-pyi",
                args=(full_module_name, OutputFile(f"_{module.name}.pyi")),
                install_path=package_path,
            )
        )

    # Make a pyi for every module
    # - they depend on every module because it needs a working environment
    #   and the user might import something
    for pyi_target in pyi_targets:
        yield BuildTarget(
            command="make-pyi",
            args=pyi_target.args + tuple(pyi_args),
            install_path=pyi_target.install_path,
        )


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
