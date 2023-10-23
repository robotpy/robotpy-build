import json
import os
from os.path import join
import pathlib
import pprint
import typing

import jinja2

from .j2_context import HeaderContext

templates_path = pathlib.Path(__file__).parent.absolute()

_emit_j2_debug = os.getenv("RPYBUILD_J2_DEBUG") == "1"


class WrapperWriter:
    def __init__(self) -> None:
        #
        # Load all the templates first
        #

        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(searchpath=templates_path),
            undefined=jinja2.StrictUndefined,
            autoescape=False,
            auto_reload=False,
            # trim_blocks=True,
            # lstrip_blocks=True,
        )

        # c++ file generated per-header
        self.header_cpp_j2 = self.env.get_template("header.cpp.j2")

        # class templates
        self.cls_tmpl_inst_cpp_j2 = self.env.get_template("cls_tmpl_inst.cpp.j2")
        self.cls_tmpl_inst_hpp_j2 = self.env.get_template("cls_tmpl_inst.hpp.j2")

        # rpy-include trampoline file
        self.rpy_include_hpp_j2 = self.env.get_template("cls_rpy_include.hpp.j2")

    def write_files(
        self,
        hctx: HeaderContext,
        name: str,
        cxx_gen_dir: str,
        hppoutdir: str,
        classdeps_json_fname: str,
    ) -> typing.List[str]:
        """Generates all files needed for a single processed header"""

        generated_sources: typing.List[str] = []

        # Jinja requires input as a dictionary
        data = hctx.__dict__

        if _emit_j2_debug:
            with open(join(cxx_gen_dir, f"{name}.txt"), "w") as fp:
                fp.write(pprint.pformat(hctx))

        # Write the cpp file first
        fname = join(cxx_gen_dir, f"{name}.cpp")
        generated_sources.append(fname)
        with open(fname, "w", encoding="utf-8") as fp:
            fp.write(self.header_cpp_j2.render(data))

        # Then the json, no need for jinja here
        with open(classdeps_json_fname, "w", encoding="utf-8") as fp:
            json.dump(hctx.class_hierarchy, fp)

        # Generate an rpy-include file for each class that has either a trampoline
        # or a template class
        for cls in hctx.classes:
            if not cls.template and not cls.trampoline:
                continue

            data["cls"] = cls
            fname = join(
                hppoutdir, f"{cls.namespace.replace(':', '_')}__{cls.cpp_name}.hpp"
            )
            with open(fname, "w", encoding="utf-8") as fp:
                fp.write(self.rpy_include_hpp_j2.render(data))

        # Each class template is instantiated in a separate cpp file to lessen
        # compiler memory requirements when compiling obnoxious templates
        if hctx.template_instances:
            # Single header output that holds all the struct outlines
            fname = join(cxx_gen_dir, f"{name}_tmpl.hpp")
            with open(fname, "w", encoding="utf-8") as fp:
                fp.write(self.cls_tmpl_inst_hpp_j2.render(data))

            # Each cpp file has a single class template instance
            for i, tmpl_data in enumerate(hctx.template_instances):
                data["tmpl_data"] = tmpl_data
                fname = join(hppoutdir, f"{name}_tmpl{i+1}.cpp")
                generated_sources.append(fname)
                with open(fname, "w", encoding="utf-8") as fp:
                    fp.write(self.cls_tmpl_inst_cpp_j2.render(data))

        return generated_sources

    def _render_template(self, tmpl_src: str, dst: str, data: dict):
        jtmpl = self.env.get_template(tmpl_src)
        content = jtmpl.render(data)
        with open(dst, "w", encoding="utf-8") as fp:
            fp.write(content)
