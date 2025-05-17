import inspect
import typing as T

from .buffer import RenderBuffer
from .context import (
    ClassContext,
    Documentation,
    EnumContext,
    FunctionContext,
    GeneratedLambda,
    PropContext,
)


def mkdoc(pre: str, doc: Documentation, post: str) -> str:
    if doc:
        if len(doc) == 1:
            return f"{pre}{doc[0]}{post}"

        sep = "\n  "
        return f"{pre}\n  {sep.join(doc)}{post}"

    return ""


def _gensig(cls_qualname: T.Optional[str], fn: FunctionContext) -> str:
    """
    py::overload_cast fails in some obscure cases, so we compute the signature here
    https://github.com/pybind/pybind11/issues/1153
    """
    if fn.const:
        trailing = " const"
    else:
        trailing = ""
    if fn.ref_qualifiers:
        trailing = f"{trailing} {fn.ref_qualifiers}"

    params = ", ".join(param.full_cpp_type for param in fn.all_params)

    return (
        f"{fn.cpp_return_type} ("
        f"{cls_qualname + '::' if cls_qualname and not fn.is_static_method else ''}*)"
        f"({params}){trailing}"
    )


def _genmethod(
    r: RenderBuffer,
    cls_qualname: T.Optional[str],
    fn: FunctionContext,
    trampoline_qualname: T.Optional[str],
    tmpl: str,
):
    qualname = cls_qualname
    arg_params = fn.filtered_params

    if fn.ifdef:
        r.writeln(f"\n#ifdef {fn.ifdef}")
        r.rel_indent(2)

    if fn.ifndef:
        r.writeln(f"\n#ifndef {fn.ifndef}")
        r.rel_indent(2)

    if fn.operator:
        r.writeln(f".def({fn.cpp_code}")
        arg_params = []
    elif fn.is_constructor:
        if fn.cpp_code:
            r.writeln(f".def(py::init({fn.cpp_code})")
        elif fn.genlambda:
            genlambda = fn.genlambda
            arg_params = genlambda.in_params
            lam_params = [param.decl for param in arg_params]
            # TODO: trampoline
            assert cls_qualname is not None
            call_qual = cls_qualname
            _gen_method_lambda(
                r,
                fn,
                genlambda,
                call_qual,
                tmpl,
                f'.def_static("{fn.py_name}"',
                lam_params,
            )
        elif trampoline_qualname:
            r.writeln(
                f".def(py::init_alias<{', '.join(param.full_cpp_type for param in arg_params)}>()"
            )
        else:
            r.writeln(
                f".def(py::init<{', '.join(param.full_cpp_type for param in arg_params)}>()"
            )
    else:
        if fn.is_static_method:
            fn_def = f'.def_static("{fn.py_name}"'
        else:
            fn_def = f'.def("{fn.py_name}"'

        if fn.cpp_code:
            cpp_code = inspect.cleandoc(fn.cpp_code)
            r.writeln(f"{fn_def}, {cpp_code}")

        elif fn.genlambda:
            genlambda = fn.genlambda
            arg_params = genlambda.in_params

            lam_params = [param.decl for param in genlambda.in_params]
            if cls_qualname:
                lam_params = [f"{cls_qualname} &self"] + lam_params

            if trampoline_qualname:
                call_qual = f"(({trampoline_qualname}*)&self)->{fn.cpp_name}"
            elif cls_qualname:
                call_qual = f"(({cls_qualname}*)&self)->{fn.cpp_name}"
            else:
                call_qual = f"{fn.namespace}::{fn.cpp_name}"

            _gen_method_lambda(r, fn, genlambda, call_qual, tmpl, fn_def, lam_params)

        else:
            if trampoline_qualname:
                fn_ns = trampoline_qualname
            elif cls_qualname:
                fn_ns = cls_qualname
            else:
                fn_ns = fn.namespace

            if trampoline_qualname:
                fn_cast = f"static_cast<{_gensig(cls_qualname, fn)}>("
                paren = ")"
            elif fn.is_overloaded:
                fn_cast = f"static_cast<{_gensig(qualname, fn)}>("
                paren = ")"
            else:
                fn_cast = ""
                paren = ""

            if tmpl:
                fn_name = f"template {fn.cpp_name}"
            else:
                fn_name = fn.cpp_name

            r.writeln(f"{fn_def}, {fn_cast}&{fn_ns}::{fn_name}{tmpl}{paren}")

    if arg_params:
        r.writeln(f"  , {', '.join(param.py_arg for param in arg_params)}")

    other_params = []

    if fn.release_gil:
        other_params.append("release_gil()")

    for nurse, patient in fn.keepalives:
        other_params.append(f"py::keep_alive<{nurse}, {patient}>()")

    if fn.return_value_policy:
        other_params.append(fn.return_value_policy)

    if other_params:
        r.writeln(f"  , {', '.join(other_params)}")

    if fn.doc:
        r.writeln(mkdoc("  , py::doc(", fn.doc, ")"))
    r.writeln(")")

    if fn.ifdef:
        r.rel_indent(-2)
        r.writeln(f"#endif // {fn.ifdef}\n")

    if fn.ifndef:
        r.rel_indent(-2)
        r.writeln(f"#endif // {fn.ifndef}\n")


def _gen_method_lambda(
    r: RenderBuffer,
    fn: FunctionContext,
    genlambda: GeneratedLambda,
    call_qual: str,
    tmpl: str,
    fn_def: str,
    lam_params: T.List[str],
):
    r.writeln(f"{fn_def}, []({', '.join(lam_params)}) {{")

    with r.indent():
        if genlambda.pre:
            r.writeln(genlambda.pre)

        call_params = ", ".join(p.call_name for p in fn.all_params)

        r.writeln(f"{genlambda.call_start}{call_qual}{tmpl}({call_params});")

        if genlambda.ret:
            r.writeln(genlambda.ret)

    r.writeln("}")


def genmethod(
    r: RenderBuffer,
    cls_qualname: T.Optional[str],
    fn: FunctionContext,
    trampoline_qualname: T.Optional[str],
):
    if not fn.template_impls:
        _genmethod(r, cls_qualname, fn, trampoline_qualname, "")
    else:
        for tmpl in fn.template_impls:
            _genmethod(
                r,
                cls_qualname,
                fn,
                trampoline_qualname,
                f"<{', '.join(tmpl)}>",
            )


def _genprop(r: RenderBuffer, qualname: str, prop: PropContext):
    doc = ""
    if prop.doc:
        doc = mkdoc(", py::doc(", prop.doc, ")")

    if prop.array_size:
        r.writeln(
            f'.def_property_readonly("{prop.py_name}", []({qualname}& self) {{\n'
            f"   return py::memoryview::from_buffer(\n"
            f"      &self.{prop.cpp_name}, sizeof({prop.cpp_type}),\n"
            f"      py::format_descriptor<{prop.cpp_type}>::value,\n"
            f"      {{{prop.array_size}}}, {{sizeof({prop.cpp_type})}},\n"
            f'      { "true" if prop.readonly else "false" }\n'
            "   );\n"
            f"}}{doc})"
        )
    elif prop.array:
        # cannot sensibly autowrap an array of incomplete size
        pass
    elif prop.reference or prop.bitfield:
        propdef = ".def_property_readonly" if prop.readonly else ".def_property"

        r.writeln(f'{propdef}("{prop.py_name}",')
        with r.indent(2):
            lines = [
                f"[](const {qualname}& self) -> {prop.cpp_type} {{ return self.{prop.cpp_name}; }}"
            ]
            if not prop.readonly:
                lines.append(
                    f"[]({qualname}& self, {prop.cpp_type} v) {{ self.{prop.cpp_name} = v; }}"
                )
            if doc:
                lines.append(doc[2:])

            r.writeln(",\n".join(lines))
        r.writeln(")")

    else:
        propdef = ".def_readonly" if prop.readonly else ".def_readwrite"
        if prop.static:
            propdef = f"{propdef}_static"

        r.writeln(f'{propdef}("{prop.py_name}", &{qualname}::{prop.cpp_name}{doc})')


def enum_decl(r: RenderBuffer, enum: EnumContext, varname: str):
    r.writeln(f"py::enum_<{ enum.full_cpp_name }> {varname};")


def enum_init_args(scope: str, enum: EnumContext):
    params = [scope, f'"{enum.py_name}"']

    if enum.arithmetic:
        params.append("py::arithmetic()")

    if enum.doc:
        params.append(mkdoc("", enum.doc, ""))

    return ", ".join(params)


def enum_def(r: RenderBuffer, varname: str, enum: EnumContext):
    for val in enum.values:
        doc = mkdoc(",", val.doc, "")
        r.writeln(f'.value("{val.py_name}", {val.full_cpp_name}{doc})')

    if enum.inline_code:
        r.write_trim(enum.inline_code)
    r.writeln(";")


def cls_user_using(r: RenderBuffer, cls: ClassContext):
    for typealias in cls.user_typealias:
        r.writeln(f"{typealias};")


def cls_auto_using(r: RenderBuffer, cls: ClassContext):
    for ccls in cls.child_classes:
        if not ccls.template:
            r.writeln(
                f"using {ccls.cpp_name} [[maybe_unused]] = typename {ccls.full_cpp_name};"
            )
    for enum in cls.enums:
        if enum.cpp_name:
            r.writeln(
                f"using {enum.cpp_name} [[maybe_unused]] = typename {enum.full_cpp_name};"
            )
    for typealias in cls.auto_typealias:
        r.writeln(f"{typealias};")


def cls_consts(r: RenderBuffer, cls: ClassContext):
    if cls.constants:
        r.writeln()
        for constant in cls.constants:
            r.writeln(f"static constexpr auto {constant[0]} = {constant[1]};")


def cls_decl(r: RenderBuffer, cls: ClassContext):
    if cls.trampoline:
        tctx = cls.trampoline
        # py::trampoline_self_life_support
        r.write_trim(
            f"""
            struct {tctx.var} : {tctx.full_cpp_name}, py::trampoline_self_life_support {{
                using RpyBase = {tctx.full_cpp_name};
                using RpyBase::RpyBase;
            }};

        """
        )
        r.writeln(
            f'static_assert(std::is_abstract<{tctx.var}>::value == false, "{cls.full_cpp_name} " SEMIWRAP_BAD_TRAMPOLINE);'
        )

    class_params = [f"typename {cls.full_cpp_name}"]
    if cls.nodelete:
        class_params.append(
            f"std::unique_ptr<typename {cls.full_cpp_name}, py::nodelete>"
        )
    else:
        class_params.append("py::smart_holder")

    if cls.trampoline:
        class_params.append(cls.trampoline.var)

    if cls.bases:
        bases = ", ".join(base.full_cpp_name_w_templates for base in cls.bases)
        class_params.append(bases)

    r.writeln(f"py::class_<{', '.join(class_params)}> {cls.var_name};")

    if cls.enums:
        r.writeln()
        for index, enum in enumerate(cls.enums, start=1):
            enum_decl(r, enum, f"{cls.var_name}_enum{index}")

    for ccls in cls.child_classes:
        if not ccls.template:
            cls_decl(r, ccls)


def cls_init(r: RenderBuffer, cls: ClassContext, name: str):

    init_params = [cls.scope_var, name]

    if cls.final:
        init_params.append("py::is_final()")

    if cls.force_multiple_inheritance:
        init_params.append("py::multiple_inheritance()")

    r.writeln(f'{cls.var_name}({", ".join(init_params)}),')

    for idx, enum in enumerate(cls.enums, start=1):
        r.writeln(f"{cls.var_name}_enum{idx}({enum_init_args(cls.var_name, enum)}),")

    for ccls in cls.child_classes:
        if not ccls.template:
            cls_init(r, ccls, f'"{ccls.py_name}"')


def cls_def_enum(r: RenderBuffer, cctx: ClassContext, varname: str):
    for idx, enum in enumerate(cctx.enums, start=1):
        r.writeln(f"{cctx.var_name}_enum{idx}")
        with r.indent():
            enum_def(r, cctx.var_name, enum)


def cls_def(r: RenderBuffer, cls: ClassContext, varname: str):
    if cls.vcheck_fns:
        for fn in cls.vcheck_fns:
            assert fn.cpp_code is not None

            r.writeln("{")
            with r.indent():
                r.writeln(f"auto vcheck = {fn.cpp_code.strip()};")

                sig_params = [f"{cls.full_cpp_name}*"]
                sig_params.extend(p.full_cpp_type for p in fn.all_params)

                signature = f"{fn.cpp_return_type}({', '.join(sig_params)})"
                r.writeln(
                    f"static_assert(std::is_convertible<decltype(vcheck), std::function<{signature}>>::value,"
                )
                r.writeln(
                    f'  "{cls.full_cpp_name}::{fn.cpp_name} must have virtual_xform if cpp_code signature doesn\'t match original function");'
                )
            r.writeln("}")

    if cls.doc:
        r.writeln(f'{varname}.doc() = {mkdoc("", cls.doc, "")};')

    r.writeln(varname)
    with r.indent():

        if cls.add_default_constructor:
            r.writeln(".def(py::init<>(), release_gil())")

        for fn in cls.wrapped_public_methods:
            genmethod(r, cls.full_cpp_name, fn, None)

        if cls.trampoline is not None:
            for fn in cls.wrapped_protected_methods:
                genmethod(r, cls.full_cpp_name, fn, cls.trampoline.var)

        for prop in cls.public_properties:
            _genprop(r, cls.full_cpp_name, prop)

        if cls.trampoline is not None:
            for prop in cls.protected_properties:
                _genprop(r, cls.trampoline.full_cpp_name, prop)

    if cls.inline_code:
        r.writeln()
        r.write_trim(cls.inline_code)

    r.writeln(";")

    if cls.unnamed_enums:
        r.writeln()
        for enum in cls.unnamed_enums:
            for val in enum.values:
                r.writeln(
                    f'{varname}.attr("{val.py_name}") = (int){val.full_cpp_name};'
                )

    for ccls in cls.child_classes:
        if not ccls.template:
            cls_def(r, ccls, ccls.var_name)
