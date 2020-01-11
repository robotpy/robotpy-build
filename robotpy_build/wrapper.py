import json
import inspect
import os
from os.path import (
    abspath,
    basename,
    dirname,
    exists,
    isdir,
    join,
    normpath,
    relpath,
    sep,
)
import posixpath
import sys
import shutil
import toposort
import typing
import yaml

from header2whatever.config import Config
from header2whatever.parse import ConfigProcessor

from setuptools import Extension

from .devcfg import get_dev_config
from .pyproject_configs import WrapperConfig
from .generator_data import MissingReporter
from .hooks import Hooks
from .hooks_datacfg import HooksDataYaml
from .download import download_and_extract_zip


class Wrapper:
    """
        Wraps downloading bindings and generating them
    """

    # Used during preprocessing
    # -> should we change this based on what flags the compiler supports?
    _cpp_version = "__cplusplus 201703L"

    def __init__(self, name, wrapcfg: WrapperConfig, setup):

        # must match PkgCfg.name
        self.name = wrapcfg.name
        # must match PkgCfg.import_name
        self.import_name = name

        self.setup_root = setup.root
        self.root = join(setup.root, *self.import_name.split("."))
        self.cfg = wrapcfg
        self.platform = setup.platform
        self.pkgcfg = setup.pkgcfg

        # Used by pkgcfg
        self.depends = self.cfg.depends

        self._all_deps = None

        if not self.cfg.artname:
            self.cfg.artname = self.cfg.name

        self.extension = None
        if self.cfg.sources or self.cfg.generate:
            define_macros = [("RPYBUILD_MODULE_NAME", self.name)]
            define_macros += [tuple(m.split(" ", 1)) for m in self.cfg.pp_defines]

            # extensions just hold data about what to actually build, we can
            # actually modify extensions all the way up until the build
            # really happens
            extname = f"{self.import_name}.{self.name}"
            self.extension = Extension(
                extname, self.cfg.sources, define_macros=define_macros, language="c++",
            )

        if self.cfg.generate and not self.cfg.generation_data:
            raise ValueError(
                "generation_data must be specified when generate is specified"
            )

        # Setup an entry point (written during build_clib)
        entry_point = f"{self.cfg.name} = {name}.pkgcfg"

        setup_kwargs = setup.setup_kwargs
        ep = setup_kwargs.setdefault("entry_points", {})
        ep.setdefault("robotpybuild", []).append(entry_point)

        self.incdir = join(self.root, "include")
        self.rpy_incdir = join(self.root, "rpy-include")

        self.dev_config = get_dev_config(self.name)

    def _dl_url(self, thing):
        # TODO: support development against locally installed things?
        base = self.cfg.baseurl
        art = self.cfg.artname
        ver = self.cfg.version
        return f"{base}/{art}/{ver}/{art}-{ver}-{thing}.zip"

    def _extract_zip_to(self, thing, dst, cache):
        download_and_extract_zip(self._dl_url(thing), to=dst, cache=cache)

    # pkgcfg interface
    def get_include_dirs(self):
        includes = [self.incdir, self.rpy_incdir]
        for h in self.cfg.extra_includes:
            includes.append(join(self.setup_root, normpath(h)))
        return includes

    def get_library_dirs(self):
        if self.get_library_names():
            return [join(self.root, "lib")]
        return []

    def get_library_names(self):
        if self.cfg.libs is None:
            return [self.cfg.name]
        else:
            return self.cfg.libs

    def get_dlopen_library_names(self):
        if self.cfg.dlopenlibs is None:
            return []
        else:
            return self.cfg.dlopenlibs

    def get_type_casters(self, casters):
        for header, types in self.cfg.type_casters.items():
            for typ in types:
                casters[typ] = header

    def all_deps(self):
        if self._all_deps is None:
            self._all_deps = self.pkgcfg.get_all_deps(self.name)
        return self._all_deps

    def _all_includes(self, include_rpyb):
        includes = self.get_include_dirs()
        for dep in self.all_deps():
            includes.extend(dep.get_include_dirs())
        if include_rpyb:
            includes.extend(self.pkgcfg.get_pkg("robotpy-build").get_include_dirs())
        return includes

    def _all_library_dirs(self):
        libs = self.get_library_dirs()
        for dep in self.cfg.depends:
            libs.extend(self.pkgcfg.get_pkg(dep).get_library_dirs())
        return libs

    def _all_library_names(self):
        libs = list(
            set(self.get_library_names()) | set(self.get_dlopen_library_names())
        )
        for dep in self.cfg.depends:
            libs.extend(self.pkgcfg.get_pkg(dep).get_library_names())
        return list(reversed(libs))

    def _all_casters(self):
        casters = {}
        for dep in self.all_deps():
            dep.get_type_casters(casters)
        self.pkgcfg.get_pkg("robotpy-build").get_type_casters(casters)
        self.get_type_casters(casters)

        # add non-namespaced versions of all casters
        # -> in theory this could lead to a conflict, but
        #    let's see how it works in practice?
        for k, v in list(casters.items()):
            k = k.split("::")[-1]
            casters[k] = v
        return casters

    def on_build_dl(self, cache):

        libdir = join(self.root, "lib")
        incdir = join(self.root, "include")
        initpy = join(self.root, "__init__.py")
        pkgcfgpy = join(self.root, "pkgcfg.py")

        # Remove downloaded/generated artifacts first
        shutil.rmtree(libdir, ignore_errors=True)
        shutil.rmtree(incdir, ignore_errors=True)

        try:
            os.unlink(initpy)
        except OSError:
            pass
        try:
            os.unlink(pkgcfgpy)
        except OSError:
            pass

        self._extract_zip_to("headers", incdir, cache)

        libnames = self.get_library_names()
        dlopen_libnames = self.get_dlopen_library_names()

        libnames = [lib for lib in libnames if lib not in dlopen_libnames]
        libnames_full = []

        if libnames or dlopen_libnames:
            libext = self.cfg.libexts.get(self.platform.libext, self.platform.libext)
            linkext = self.cfg.linkexts.get(
                self.platform.linkext, self.platform.linkext
            )

            libnames_full = [
                f"{self.platform.libprefix}{lib}{libext}" for lib in libnames
            ]
            libnames_full += [
                f"{self.platform.libprefix}{lib}{libext}" for lib in dlopen_libnames
            ]

            extract_names = libnames_full[:]

            if libext != linkext:
                extract_names += [
                    f"{self.platform.libprefix}{lib}{linkext}" for lib in libnames
                ]

            os.makedirs(libdir)
            to = {
                posixpath.join(
                    self.platform.os, self.platform.arch, "shared", libname
                ): join(libdir, libname)
                for libname in extract_names
            }

            self._extract_zip_to(f"{self.platform.os}{self.platform.arch}", to, cache)

        self._write_init_py(initpy, libnames_full)
        self._write_pkgcfg_py(pkgcfgpy)

    def _write_init_py(self, fname, libnames):
        init = inspect.cleandoc(
            """

        # fmt: off
        # This file is automatically generated, DO NOT EDIT

        from os.path import abspath, join, dirname
        _root = abspath(dirname(__file__))

        ##IMPORTS##

        from ctypes import cdll

        """
        )

        init += "\n"

        if libnames:
            for libname in libnames:
                init += f'_lib = cdll.LoadLibrary(join(_root, "lib", "{libname}"))\n'

        imports = []
        for dep in self.cfg.depends:
            pkg = self.pkgcfg.get_pkg(dep)
            if pkg.import_name:
                imports.append(pkg.import_name)

        if imports:
            imports = "# runtime dependencies\nimport " + "\nimport ".join(imports)
        else:
            imports = ""

        init = init.replace("##IMPORTS##", imports)

        with open(join(self.root, "__init__.py"), "w") as fp:
            fp.write(init)

    def _write_pkgcfg_py(self, fname):

        library_dirs = "[]"
        library_names = self.get_library_names()
        if library_names:
            library_dirs = '[join(_root, "lib")]'

        # write pkgcfg.py
        pkgcfg = inspect.cleandoc(
            f"""
        # fmt: off
        # This file is automatically generated, DO NOT EDIT

        from os.path import abspath, join, dirname
        _root = abspath(dirname(__file__))

        import_name = "{self.import_name}"
        depends = {repr(self.cfg.depends)}

        def get_include_dirs():
            return [join(_root, "include"), join(_root, "rpy-include")##EXTRAINCLUDES##]

        def get_library_dirs():
            return {library_dirs}
        
        def get_library_names():
            return {repr(library_names)}
        """
        )

        extraincludes = ""
        if self.cfg.extra_includes:
            # these are relative to the root of the project, need
            # to resolve the path relative to the pkgcfg directory
            pth = join(*self.import_name.split("."))

            for h in self.cfg.extra_includes:
                h = '", "'.join(relpath(normpath(h), pth).split(sep))
                extraincludes += f', join(_root, "{h}")'

        pkgcfg = pkgcfg.replace("##EXTRAINCLUDES##", extraincludes)

        type_casters = {}
        self.get_type_casters(type_casters)
        if type_casters:
            pkgcfg += (
                f"\n\ndef get_type_casters(casters):\n"
                f"    casters.update({repr(type_casters)})\n"
            )

        with open(fname, "w") as fp:
            fp.write(pkgcfg)

    def _load_generation_data(self, datafile):
        with open(datafile) as fp:
            data = yaml.safe_load(fp)

        if data is None:
            data = {}

        return HooksDataYaml(**data)

    def on_build_gen(
        self, cxx_gen_dir, missing_reporter: typing.Optional[MissingReporter] = None
    ):

        if not self.cfg.generate:
            return

        if missing_reporter:
            report_only = True
        else:
            report_only = False
            missing_reporter = MissingReporter()

        thisdir = abspath(dirname(__file__))

        hppoutdir = join(self.rpy_incdir, "rpygen")
        tmpl_dir = join(thisdir, "templates")
        cpp_tmpl = join(tmpl_dir, "gen_pybind11.cpp.j2")
        hpp_tmpl = join(tmpl_dir, "gen_cls_trampoline.hpp.j2")
        classdeps_tmpl = join(tmpl_dir, "gen_classdeps.json.j2")

        pp_includes = self._all_includes(False)

        # TODO: only regenerate files if the generated files
        #       have changed
        if not report_only:

            if self.dev_config.only_generate is None:
                shutil.rmtree(cxx_gen_dir, ignore_errors=True)
                shutil.rmtree(hppoutdir, ignore_errors=True)

            os.makedirs(cxx_gen_dir, exist_ok=True)
            os.makedirs(hppoutdir, exist_ok=True)

        per_header = False
        data_fname = self.cfg.generation_data
        if self.cfg.generation_data:
            datapath = join(self.setup_root, normpath(self.cfg.generation_data))
            per_header = isdir(datapath)
            if not per_header:
                data = self._load_generation_data(datapath)
        else:
            data = HooksDataYaml()

        sources = self.cfg.sources[:]
        pp_defines = [self._cpp_version] + self.cfg.pp_defines
        casters = self._all_casters()

        # These are written to file to make it easier for dev mode to work
        classdeps = {}

        processor = ConfigProcessor(tmpl_dir)

        if self.dev_config.only_generate is not None:
            only_generate = {n: True for n in self.dev_config.only_generate}
        else:
            only_generate = None

        generation_search_path = [self.root,] + self.get_include_dirs()

        for gen in self.cfg.generate:
            for name, header in gen.items():

                header = normpath(header)
                for path in generation_search_path:
                    header_path = join(path, header)
                    if exists(header_path):
                        break
                else:
                    raise ValueError("could not find " + header)

                if report_only:
                    templates = []
                    class_templates = []
                else:
                    cpp_dst = join(cxx_gen_dir, f"{name}.cpp")
                    sources.append(cpp_dst)
                    classdeps_dst = join(cxx_gen_dir, f"{name}.json")
                    classdeps[name] = classdeps_dst

                    hpp_dst = join(
                        hppoutdir,
                        "{{ cls['namespace'] | replace(':', '_') }}__{{ cls['name'] }}.hpp",
                    )

                    templates = [
                        {"src": cpp_tmpl, "dst": cpp_dst},
                        {"src": classdeps_tmpl, "dst": classdeps_dst},
                    ]
                    class_templates = [{"src": hpp_tmpl, "dst": hpp_dst}]

                if only_generate is not None and not only_generate.pop(name, False):
                    continue

                if per_header:
                    data_fname = join(datapath, name + ".yml")
                    if not exists(data_fname):
                        print("WARNING: could not find", data_fname)
                        data = HooksDataYaml()
                    else:
                        data = self._load_generation_data(data_fname)

                # for each thing, create a h2w configuration dictionary
                cfgd = {
                    # generation code depends on this being just one header!
                    "headers": [header_path],
                    "templates": templates,
                    "class_templates": class_templates,
                    "preprocess": True,
                    "pp_retain_all_content": False,
                    "pp_include_paths": pp_includes,
                    "pp_defines": pp_defines,
                    "vars": {"mod_fn": name},
                }

                cfg = Config(cfgd)
                cfg.validate()
                cfg.root = self.incdir

                hooks = Hooks(data, casters)
                processor.process_config(cfg, data, hooks)

                hooks.report_missing(data_fname, missing_reporter)

        if only_generate:
            unused = ", ".join(sorted(only_generate))
            raise ValueError(f"only_generate specified unused headers! {unused}")

        if not report_only:
            for name, contents in missing_reporter.as_yaml():
                print("WARNING: some items not in generation yaml for", basename(name))
                print(contents)

        # generate an inline file that can be included + called
        if not report_only:
            self._write_wrapper_hpp(cxx_gen_dir, classdeps)
            gen_includes = [cxx_gen_dir]
        else:
            gen_includes = []

        # Add the root to the includes (but only privately)
        root_includes = [self.root]

        # update the build extension so that build_ext works
        self.extension.sources = sources
        self.extension.include_dirs = (
            self._all_includes(True) + gen_includes + root_includes
        )
        self.extension.library_dirs = self._all_library_dirs()
        self.extension.libraries = self._all_library_names()

    def _write_wrapper_hpp(self, outdir, classdeps):

        decls = []
        calls = []

        def _clean(n):
            tmpl_idx = n.find("<")
            if tmpl_idx != -1:
                n = n[:tmpl_idx]
            return n

        # Need to ensure that wrapper initialization is called in base order
        # so we have to toposort it here. The data is written at gen time
        # to JSON files
        types2name = {}
        types2deps = {}
        ordering = []

        for name, jsonfile in classdeps.items():
            with open(jsonfile) as fp:
                dep = json.load(fp)

            # make sure objects without classes are also included!
            if not dep:
                ordering.append(name)

            for clsname, bases in dep.items():
                clsname = _clean(clsname)
                if clsname in types2name:
                    raise ValueError(f"duplicate class {clsname}")
                types2name[clsname] = name
                types2deps[clsname] = [_clean(base) for base in bases]

        to_sort = {}
        for clsname, bases in types2deps.items():
            clsname = types2name[clsname]
            deps = to_sort.setdefault(clsname, set())
            for base in bases:
                base = types2name.get(base)
                if base and base != clsname:
                    deps.add(base)

        ordering.extend(toposort.toposort_flatten(to_sort, sort=True))

        for name in ordering:
            decls.append(f"void init_{name}(py::module &m);")
            calls.append(f"    init_{name}(m);")

        content = (
            inspect.cleandoc(
                """

        // This file is autogenerated, DO NOT EDIT
        #pragma once
        #include <robotpy_build.h>

        // forward declarations
        ##DECLS##

        static void initWrapper(py::module &m) {
        ##CALLS##
        }
        
        """
            )
            .replace("##DECLS##", "\n".join(decls))
            .replace("##CALLS##", "\n".join(calls))
        )

        with open(join(outdir, "rpygen_wrapper.hpp"), "w") as fp:
            fp.write(content)
