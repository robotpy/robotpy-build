import json
import os
from os.path import join
import pprint
import typing

from .context import HeaderContext
from .render_wrapped import render_wrapped_cpp
from .render_cls_rpy_include import render_cls_rpy_include_hpp
from .render_tmpl_inst import render_template_inst_cpp, render_template_inst_hpp

_emit_j2_debug = os.getenv("RPYBUILD_J2_DEBUG") == "1"


class WrapperWriter:

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
            fp.write(render_wrapped_cpp(hctx))

        # Then the json
        with open(classdeps_json_fname, "w", encoding="utf-8") as fp:
            json.dump(hctx.class_hierarchy, fp)

        # Generate an rpy-include file for each class that has either a trampoline
        # or a template class
        for cls in hctx.classes:
            if not cls.template and not cls.trampoline:
                continue

            fname = join(
                hppoutdir, f"{cls.namespace.replace(':', '_')}__{cls.cpp_name}.hpp"
            )
            with open(fname, "w", encoding="utf-8") as fp:
                fp.write(render_cls_rpy_include_hpp(hctx, cls))

        # Each class template is instantiated in a separate cpp file to lessen
        # compiler memory requirements when compiling obnoxious templates
        if hctx.template_instances:
            # Single header output that holds all the struct outlines
            fname = join(cxx_gen_dir, f"{name}_tmpl.hpp")
            with open(fname, "w", encoding="utf-8") as fp:
                fp.write(render_template_inst_hpp(hctx))

            # Each cpp file has a single class template instance
            for i, tmpl_data in enumerate(hctx.template_instances):
                data["tmpl_data"] = tmpl_data
                fname = join(hppoutdir, f"{name}_tmpl{i+1}.cpp")
                generated_sources.append(fname)
                with open(fname, "w", encoding="utf-8") as fp:
                    fp.write(render_template_inst_cpp(hctx, tmpl_data))

        return generated_sources
