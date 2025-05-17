from .buffer import RenderBuffer
from .context import HeaderContext

from . import render_pybind11 as rpybind11
from .render_cls_prologue import render_class_prologue


def render_wrapped_cpp(hctx: HeaderContext) -> str:
    """
    This contains the primary binding code generated from parsing a single
    header file. There are also per-class headers generated (templates,
    trampolines), and those are included/used by this.
    """
    r = RenderBuffer()

    render_class_prologue(r, hctx)

    if hctx.template_instances:
        r.writeln(f'\n#include "{hctx.hname}_tmpl.hpp"')

    if hctx.extra_includes:
        r.writeln()
        for inc in hctx.extra_includes:
            r.writeln(f"#include <{inc}>")

    if hctx.user_typealias:
        r.writeln()
        for typealias in hctx.user_typealias:
            r.writeln(f"{typealias};")

    #
    # Ordering of the initialization function
    #
    # - namespace/typealiases
    # - global enums
    # - templates (because CRTP)
    # - class declarations
    # - class enums
    # - class methods
    # - global methods
    #
    # Additionally, we use two-part initialization to ensure that documentation
    # strings are generated properly. First part is to register the class with
    # pybind11, second part is to generate all the methods/etc for it.
    #
    # TODO: make type_traits optional by detecting trampoline

    r.writeln("\n#include <type_traits>")

    if hctx.namespaces:
        r.writeln()
        for ns in hctx.namespaces:
            r.writeln(f"using namespace {ns};")

    r.writeln(f"\nstruct semiwrap_{hctx.hname}_initializer {{\n")

    with r.indent():
        for cls in hctx.classes:
            if not cls.template:
                rpybind11.cls_user_using(r, cls)
                rpybind11.cls_consts(r, cls)

        if hctx.subpackages:
            r.writeln()
            for vname in hctx.subpackages.values():
                r.writeln(f"py::module {vname};")

        # enums
        for index, enum in enumerate(hctx.enums, start=1):
            rpybind11.enum_decl(r, enum, f"enum{index}")

        # template decls
        for tmpl_data in hctx.template_instances:
            if not tmpl_data.matched:
                r.writeln(f"swgen::{tmpl_data.binder_typename} {tmpl_data.var_name};")

        # class decls
        for cls in hctx.classes:
            if cls.template is None:
                r.writeln()
                rpybind11.cls_decl(r, cls)
            elif cls.template.instances:
                r.writeln()
                for tmpl_data in cls.template.instances:
                    r.writeln(
                        f"swgen::{tmpl_data.binder_typename} {tmpl_data.var_name};"
                    )

        r.writeln("\npy::module &m;\n")
        r.writeln(f"semiwrap_{hctx.hname}_initializer(py::module &m) :")

        with r.indent():
            for pkg, vname in hctx.subpackages.items():
                r.writeln(f'{vname}(m.def_submodule("{pkg}")),')

            for index, enum in enumerate(hctx.enums, start=1):
                r.writeln(
                    f"enum{index}({rpybind11.enum_init_args(enum.scope_var, enum)}),"
                )

            for tmpl_data in hctx.template_instances:
                if not tmpl_data.matched:
                    r.writeln(
                        f'{tmpl_data.var_name}({tmpl_data.scope_var}, "{tmpl_data.py_name}"),'
                    )

            for cls in hctx.classes:
                if not cls.template:
                    rpybind11.cls_init(r, cls, f'"{cls.py_name}"')
                else:
                    for tmpl_data in cls.template.instances:
                        r.writeln(
                            f'{tmpl_data.var_name}({tmpl_data.scope_var}, "{tmpl_data.py_name}"),'
                        )

            r.writeln("m(m)")

        if hctx.enums or hctx.classes:
            r.writeln("{")
            with r.indent():
                # enums can go in the initializer because they cant have dependencies,
                # and then we dont need to figure out class dependencies for enum arguments

                for index, enum in enumerate(hctx.enums, start=1):
                    r.writeln(f"enum{index}")
                    with r.indent():
                        rpybind11.enum_def(r, enum.scope_var, enum)

                for cls in hctx.classes:
                    rpybind11.cls_def_enum(r, cls, cls.var_name)
                    for ccls in cls.child_classes:
                        rpybind11.cls_def_enum(r, ccls, ccls.var_name)
            r.writeln("}")
        else:
            r.writeln("{}")

        r.writeln("\nvoid finish() {\n")

        with r.indent():

            # Templates
            for tdata in hctx.template_instances:
                r.writeln(f"\n{tdata.var_name}.finish(")
                with r.indent():
                    if tdata.doc_set:
                        r.writeln(f'{rpybind11.mkdoc("", tdata.doc_set, "")},')
                    else:
                        r.writeln("nullptr,")

                    if tdata.doc_add:
                        r.writeln(rpybind11.mkdoc("", tdata.doc_add, ""))
                    else:
                        r.writeln("nullptr")
                r.writeln(");")

            # Class methods
            for cls in hctx.classes:
                if not cls.template:
                    r.writeln("{")
                    with r.indent():
                        rpybind11.cls_auto_using(r, cls)
                        rpybind11.cls_def(r, cls, cls.var_name)
                    r.writeln("}")

            # Global methods
            if hctx.functions:
                r.writeln()
                for fn in hctx.functions:
                    if not fn.ignore_py:
                        r.writeln(fn.scope_var)
                        with r.indent(1):
                            rpybind11.genmethod(r, None, fn, None)
                        r.writeln(";")

            if hctx.inline_code:
                r.writeln()
                r.write_trim(hctx.inline_code)

        r.writeln("}")

    r.writeln(
        f"}}; // struct semiwrap_{hctx.hname}_initializer\n"
        "\n"
        f"static std::unique_ptr<semiwrap_{hctx.hname}_initializer> cls;\n"
        "\n"
        f"void begin_init_{hctx.hname}(py::module &m) {{\n"
        f"  cls = std::make_unique<semiwrap_{hctx.hname}_initializer>(m);\n"
        "}\n"
        "\n"
        f"void finish_init_{hctx.hname}() {{\n"
        "  cls->finish();\n"
        "  cls.reset();\n"
        "}\n"
    )

    return r.getvalue()
