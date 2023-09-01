from dataclasses import dataclass
from keyword import iskeyword
import re
import sphinxify
import sys
import typing

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    Protocol = object  # pragma: no cover

from ..config.autowrap_yml import (
    AutowrapConfigYaml,
    BufferData,
    BufferType,
    EnumData,
    EnumValue,
    FunctionData,
    ParamData,
    PropAccess,
    ReturnValuePolicy,
)
from .generator_data import GeneratorData, MissingReporter
from .mangle import trampoline_signature

from .j2_context import (
    BaseClassData,
    ClassContext,
    ClassTemplateData,
    Documentation,
    EnumContext,
    EnumeratorContext,
    FunctionContext,
    GeneratedLambda,
    HeaderContext,
    OverloadTracker,
    ParamContext,
    PropContext,
    TemplateInstanceContext,
    TrampolineData,
)


# TODO: this isn't the best solution
def _gen_int_types():
    for i in ("int", "uint"):
        for j in ("", "_fast", "_least"):
            for k in ("8", "16", "32", "64"):
                yield f"{i}{j}{k}_t"
    yield "intmax_t"
    yield "uintmax_t"


_int32_types = frozenset(_gen_int_types())


_rvp_map = {
    ReturnValuePolicy.TAKE_OWNERSHIP: ", py::return_value_policy::take_ownership",
    ReturnValuePolicy.COPY: ", py::return_value_policy::copy",
    ReturnValuePolicy.MOVE: ", py::return_value_policy::move",
    ReturnValuePolicy.REFERENCE: ", py::return_value_policy::reference",
    ReturnValuePolicy.REFERENCE_INTERNAL: ", py::return_value_policy::reference_internal",
    ReturnValuePolicy.AUTOMATIC: "",
    ReturnValuePolicy.AUTOMATIC_REFERENCE: ", py::return_value_policy::automatic_reference",
}

# fmt: off
_operators = {
    # binary
    "-", "+", "*", "/", "%", "&", "^", "==", "!=", "|", ">", ">=", "<", "<=",
    # inplace
    "+=", "-=", "*=", "/=", "%=", "&=", "^=", "|=",
}
# fmt: on

_type_caster_seps = re.compile(r"[<>\(\)]")

_lambda_predent = "          "

_default_param_data = ParamData()
_default_enum_value = EnumValue()


@dataclass
class _ReturnParamContext:
    #: was x_type
    cpp_type: str

    #: If this is an out parameter, the name of the parameter
    cpp_retname: str


class HasSubpackage(Protocol):
    subpackage: str


class HasDoc(Protocol):
    doc: str
    doc_append: str


class HasNameData(Protocol):
    rename: str


class HookError(Exception):
    pass


def _using_signature(cls: ClassContext, fn: FunctionContext) -> str:
    return f"{cls.full_cpp_name_identifier}_{fn.cpp_name}"


class Hooks:
    """
    Header2Whatever hooks used for generating C++ wrappers
    """

    _qualname_bad = ":<>="
    _qualname_trans = str.maketrans(_qualname_bad, "_" * len(_qualname_bad))

    def __init__(
        self,
        data: AutowrapConfigYaml,
        casters: typing.Dict[str, typing.Dict[str, typing.Any]],
        report_only: bool,
        hname: str,
    ):
        self.gendata = GeneratorData(data)
        self.rawdata = data
        self.casters = casters
        self.report_only = report_only

        self.types: typing.Set[str] = set()

        self.hctx = HeaderContext(
            hname=hname,
            extra_includes=data.extra_includes,
            extra_includes_first=data.extra_includes_first,
            inline_code=data.inline_code,
            trampoline_signature=trampoline_signature,
            using_signature=_using_signature,
        )

    def report_missing(self, name: str, reporter: MissingReporter):
        self.gendata.report_missing(name, reporter)

    def _add_type_caster(self, typename: str):
        # defer until the end since there's lots of duplication
        self.types.add(typename)

    def _get_module_var(self, data: HasSubpackage) -> str:
        if data.subpackage:
            var = f"pkg_{data.subpackage.replace('.', '_')}"
            self.hctx.subpackages[data.subpackage] = var
            return var

        return "m"

    def _get_type_caster_cfgs(self, typename: str):
        tmpl_idx = typename.find("<")
        if tmpl_idx == -1:
            typenames = [typename]
        else:
            typenames = [typename[:tmpl_idx]] + _type_caster_seps.split(
                typename[tmpl_idx:].replace(" ", "")
            )
        for typename in typenames:
            if typename:
                ccfg = self.casters.get(typename)
                if ccfg:
                    yield ccfg

    def _get_type_caster_includes(self):
        includes = set()
        for typename in self.types:
            for ccfg in self._get_type_caster_cfgs(typename):
                includes.add(ccfg["hdr"])
        return sorted(includes)

    def _make_py_name(
        self,
        name: str,
        data: HasNameData,
        strip_prefixes: typing.Optional[typing.List[str]] = None,
        is_operator=False,
    ):
        if data.rename:
            return data.rename

        if strip_prefixes is None:
            strip_prefixes = self.rawdata.strip_prefixes

        if strip_prefixes:
            for pfx in strip_prefixes:
                if name.startswith(pfx):
                    n = name[len(pfx) :]
                    if n.isidentifier():
                        name = n
                        break

        if iskeyword(name):
            return f"{name}_"
        if not name.isidentifier() and not is_operator:
            if not self.report_only:
                raise ValueError(f"name {name!r} is not a valid identifier")

        return name

    def _process_doc(
        self,
        thing,
        data: HasDoc,
        append_prefix="",
        param_remap: typing.Dict[str, str] = {},
    ) -> Documentation:
        doc = ""

        if data.doc is not None:
            doc = data.doc
        elif "doxygen" in thing:
            doc = thing["doxygen"]
            if param_remap:
                d = sphinxify.Doc.from_comment(doc)
                for param in d.params:
                    new_name = param_remap.get(param.name)
                    if new_name:
                        param.name = new_name
                doc = str(d)
            else:
                doc = sphinxify.process_raw(doc)

        if data.doc_append is not None:
            doc += f"\n{append_prefix}" + data.doc_append.replace(
                "\n", f"\n{append_prefix}"
            )

        return self._quote_doc(doc)

    def _quote_doc(self, doc: typing.Optional[str]) -> Documentation:
        doc_quoted: Documentation = None
        if doc:
            # TODO
            doc = doc.replace("\\", "\\\\").replace('"', '\\"')
            doc_quoted = doc.splitlines(keepends=True)
            doc_quoted = ['"%s"' % (dq.replace("\n", "\\n"),) for dq in doc_quoted]

        return doc_quoted

    def _resolve_default(self, fn, p, name, cpp_type) -> str:
        if isinstance(name, (int, float)):
            return str(name)
        if name in ("NULL", "nullptr"):
            return name

        if name and name[0] == "{" and name[-1] == "}":
            if p["array"]:
                return name
            return f"{cpp_type}{name}"

        # if there's a parent, look there
        parent = fn["parent"]
        if parent:
            for prop in parent["properties"]["public"]:
                if prop["name"] == name:
                    name = f"{parent['namespace']}::{parent['name']}::{name}"
        return name

    def _add_default_arg_cast(self, p, name, cpp_type):
        found_typename = None
        for ccfg in self._get_type_caster_cfgs(cpp_type):
            if ccfg.get("darg"):
                if found_typename and found_typename != ccfg["typename"]:
                    raise HookError(
                        f"multiple type casters found for {p['name']} ({cpp_type}), use disable_type_caster_default_cast"
                    )
                found_typename = ccfg["typename"]
                name = f"({found_typename}){name}"

        return name

    def _get_function_signature(self, fn):
        param_sig = ", ".join(
            p.get("enum", p["raw_type"]) + "&" * p["reference"] + "*" * p["pointer"]
            for p in fn["parameters"]
        )
        param_sig = param_sig.replace(" >", ">")
        if fn["const"]:
            if param_sig:
                param_sig += " [const]"
            else:
                param_sig = "[const]"

        return param_sig

    def _process_base_param(self, decl_param):
        params = decl_param.get("params")
        if params:
            # recurse
            params = [self._process_base_param(param) for param in params]
            return f"{decl_param['param']}<{', '.join(params)}>"
        else:
            return decl_param["param"]

    def _make_base_params(
        self, base_decl_params, pybase_params: typing.Set[str]
    ) -> str:
        base_params = [
            self._process_base_param(decl_param) for decl_param in base_decl_params
        ]

        for decl_param in base_params:
            pybase_params.add(decl_param)

        return ", ".join(base_params)

    def _extract_typealias(
        self,
        in_ta: typing.List[str],
        out_ta: typing.List[str],
        ta_names: typing.Set[str],
    ):
        for typealias in in_ta:
            if typealias.startswith("template"):
                out_ta.append(typealias)
            else:
                teq = typealias.find("=")
                if teq != -1:
                    ta_name = typealias[:teq].strip()
                    out_ta.append(f"using {typealias}")
                else:
                    ta_name = typealias.split("::")[-1]
                    out_ta.append(f"using {ta_name} = {typealias}")
                ta_names.add(ta_name)

    def _enum_hook(
        self, cpp_scope: str, scope_var: str, var_name: str, en, enum_data: EnumData
    ) -> EnumContext:
        value_prefix = None
        strip_prefixes = []
        values: typing.List[EnumeratorContext] = []

        py_name = ""
        full_cpp_name = ""
        value_scope = cpp_scope

        ename = en.get("name", "")

        if ename:
            full_cpp_name = f"{cpp_scope}{ename}"
            value_scope = f"{full_cpp_name}::"
            py_name = self._make_py_name(ename, enum_data)

            value_prefix = enum_data.value_prefix
            if not value_prefix:
                value_prefix = ename

            strip_prefixes = [f"{value_prefix}_", value_prefix]

        for v in en["values"]:
            name = v["name"]
            v_data = enum_data.values.get(name, _default_enum_value)
            if v_data.ignore:
                continue

            values.append(
                EnumeratorContext(
                    full_cpp_name=f"{value_scope}{name}",
                    py_name=self._make_py_name(name, v_data, strip_prefixes),
                    doc=self._process_doc(v, v_data, append_prefix="  "),
                )
            )

        return EnumContext(
            scope_var=scope_var,
            var_name=var_name,
            full_cpp_name=full_cpp_name,
            py_name=py_name,
            values=values,
            doc=self._process_doc(en, enum_data),
            arithmetic=enum_data.arithmetic,
            inline_code=enum_data.inline_code,
        )

    def header_hook(self, header, data):
        """Called for each header"""

        self.hctx.rel_fname = header.rel_fname

        for using in header.using.values():
            if using["using_type"] == "declaration":
                self.hctx.using_declarations.append(using["raw_type"])

        for i, en in enumerate(header.enums):
            enum_data = self.gendata.get_enum_data(en.get("name"))

            if not enum_data.ignore:
                scope_var = self._get_module_var(enum_data)
                var_name = f"enum{i}"
                self.hctx.enums.append(
                    self._enum_hook(en["namespace"], scope_var, var_name, en, enum_data)
                )

        for v in header.variables:
            # TODO: in theory this is used to wrap global variables, but it's
            # currently totally ignored
            self.gendata.get_prop_data(v["name"])
            self._add_type_caster(v["raw_type"])

        for _, u in header.using.items():
            self._add_type_caster(u["raw_type"])

        for i, (k, tmpl_data) in enumerate(data["data"].templates.items()):
            qualname = tmpl_data.qualname
            if "::" not in qualname:
                qualname = f"::{qualname}"
            qualname = qualname.translate(self._qualname_trans)

            doc_add = tmpl_data.doc_append
            if doc_add:
                doc_add = f"\n{doc_add}"

            # TODO: this should be a list, not a dict
            self.hctx.template_instances[str(i)] = TemplateInstanceContext(
                scope_var=self._get_module_var(tmpl_data),
                var_name=f"tmplCls{i}",
                py_name=k,
                full_cpp_name_identifier=qualname,
                binder_typename=f"bind_{qualname}_{i}",
                params=tmpl_data.params,
                header_name=f"{qualname}.hpp",
                doc_set=self._quote_doc(tmpl_data.doc),
                doc_add=self._quote_doc(doc_add),
            )

            for param in tmpl_data.params:
                self._add_type_caster(param)

        self.hctx.type_caster_includes = self._get_type_caster_includes()

        user_typealias = []
        self._extract_typealias(self.rawdata.typealias, user_typealias, set())
        self.hctx.user_typealias = user_typealias

        # h2w data should only contain our data for future h2w removal
        skip_generation = data["skip_generation"]
        data.clear()
        data["skip_generation"] = skip_generation
        data.update(self.hctx.__dict__)

    def _function_hook(
        self,
        fn,
        data: FunctionData,
        scope_var: str,
        internal: bool,
        overload_tracker: OverloadTracker,
    ) -> FunctionContext:
        """shared with methods/functions"""

        # if cpp_code is specified, don't release the gil unless the user
        # specifically asks for it
        if data.no_release_gil is None:
            if data.cpp_code:
                data.no_release_gil = True

        x_all_params: typing.List[ParamContext] = []
        x_in_params: typing.List[ParamContext] = []
        out_params: typing.List[ParamContext] = []
        x_filtered_params: typing.List[ParamContext] = []
        x_rets: typing.List[_ReturnParamContext] = []
        x_temps: typing.List[ParamContext] = []
        keepalives = []

        param_remap = {}

        has_buffers = len(data.buffers) > 0
        need_lambda = False
        genlambda: typing.Optional[GeneratedLambda] = None
        lambda_pre: typing.List[str] = []

        # Use this if one of the parameter types don't quite match
        param_override = data.param_override

        # buffers: accepts a python object that supports the buffer protocol
        #          as input. If the buffer is an 'out' buffer, then it
        #          will request a writeable buffer. Data is written by the
        #          wrapped function to that buffer directly, and the length
        #          written (if the length is a pointer) will be returned
        buffer_params: typing.Dict[str, BufferData] = {}
        buflen_params: typing.Dict[str, BufferData] = {}
        if data.buffers:
            for bufinfo in data.buffers:
                if bufinfo.src == bufinfo.len:
                    raise ValueError(
                        f"buffer src({bufinfo.src}) and len({bufinfo.len}) cannot be the same"
                    )
                buffer_params[bufinfo.src] = bufinfo
                buflen_params[bufinfo.len] = bufinfo

        is_constructor = fn.get("constructor")
        fn_disable_none = data.disable_none

        # Process parameters

        for i, p in enumerate(fn["parameters"]):
            p_const = bool(p["constant"])
            p_reference = p["reference"]
            p_pointer = p["pointer"]

            # automatically retain references passed to constructors
            if is_constructor and p_reference == 1:
                keepalives.append((1, i + 2))

            if p["raw_type"] in _int32_types:
                fundamental = True
            else:
                fundamental = p["fundamental"]

            cpp_type_no_const = p.get("enum", p["raw_type"])
            cpp_type = cpp_type_no_const

            p_name = p["name"]
            orig_pname = p_name
            if p_name == "":
                p_name = f"param{i}"

            if p_pointer:
                call_name = p_name
            elif p_reference:
                call_name = f"std::forward<decltype({p['name']})>({p['name']})"
            else:
                call_name = f"std::move({p['name']})"

            # This is different because call_name might get special treatment later
            virtual_call_name = call_name
            cpp_retname = orig_pname

            # TODO: this is precarious
            # - needs to override some things
            force_out = False
            default = None
            disable_none = fn_disable_none
            po = param_override.get(p_name)
            if po:
                force_out = po.force_out
                if po.name:
                    p_name = po.name
                if po.x_type:
                    cpp_type = po.x_type
                if po.default:
                    default = po.default
                if po.disable_none is not None:
                    disable_none = po.disable_none
            else:
                po = _default_param_data

            py_pname = p_name
            if iskeyword(py_pname):
                py_pname = f"{py_pname}_"

            if orig_pname != py_pname:
                param_remap[orig_pname] = py_pname

            # Autodetect disable_none if not explicitly specified
            if disable_none is None:
                disable_none = cpp_type.startswith("std::function")

            if disable_none:
                py_arg = f'py::arg("{py_pname}").none(false)'
            else:
                py_arg = f'py::arg("{py_pname}")'

            default = default or p.get("default", None)
            if default:
                default = self._resolve_default(fn, p, default, cpp_type)
                if not po.disable_type_caster_default_cast:
                    default = self._add_default_arg_cast(p, default, cpp_type)
                if default:
                    py_arg = f"{py_arg} = {default}"

            ptype = "in"

            buflen = buflen_params.pop(p_name, None)

            if p_name in buffer_params:
                bufinfo = buffer_params.pop(p_name)
                need_lambda = True
                bname = f"__{bufinfo.src}"
                p_const = True
                p_reference = 1
                p_pointer = 0

                call_name = f"({cpp_type}*){bname}.ptr"
                cpp_type = "py::buffer"

                # this doesn't seem to be true for bytearrays, which is silly
                # x_lambda_pre.append(
                #     f'if (PyBuffer_IsContiguous((Py_buffer*){p_name}.ptr(), \'C\') == 0) throw py::value_error("{p_name}: buffer must be contiguous")'
                # )

                # TODO: check for dimensions, strides, other dangerous things

                # bufinfo was validated and converted before it got here
                if bufinfo.type is BufferType.IN:
                    ptype = "in"
                    lambda_pre += [f"auto {bname} = {p_name}.request(false)"]
                else:
                    ptype = "in"
                    lambda_pre += [f"auto {bname} = {p_name}.request(true)"]

                lambda_pre += [f"{bufinfo.len} = {bname}.size * {bname}.itemsize"]

                if bufinfo.minsz:
                    lambda_pre.append(
                        f'if ({bufinfo.len} < {bufinfo.minsz}) throw py::value_error("{p_name}: minimum buffer size is {bufinfo.minsz}")'
                    )

            elif buflen:
                if p_pointer:
                    call_name = f"&{buflen.len}"
                    ptype = "out"
                else:
                    # if it's not a pointer, then the called function
                    # can't communicate through it, so ignore the parameter
                    need_lambda = True
                    call_name = buflen.len
                    ptype = "tmp"

            elif force_out or (
                (p_pointer or p_reference == 1) and not p_const and fundamental
            ):
                if p_pointer:
                    call_name = f"&{call_name}"
                else:
                    call_name = p_name

                ptype = "out"
            elif p["array"]:
                asz = po.array_size or p.get("array_size", 0)
                if asz:
                    cpp_type = f"std::array<{cpp_type}, {asz}>"
                    call_name = f"{call_name}.data()"
                    if not default:
                        default = "{}"
                else:
                    # it's a vector
                    pass
                ptype = "out"

            self._add_type_caster(cpp_type)

            if p_const:
                cpp_type = f"const {cpp_type}"

            x_type_full = cpp_type
            x_type_full += "&" * p_reference
            x_type_full += "*" * p_pointer

            x_decl = f"{x_type_full} {p_name}"

            pctx = ParamContext(
                arg_name=p_name,
                full_cpp_type=x_type_full,
                cpp_type=cpp_type,
                cpp_type_no_const=cpp_type_no_const,
                default=default,
                decl=x_decl,
                py_arg=py_arg,
                call_name=call_name,
                virtual_call_name=virtual_call_name,
                cpp_retname=cpp_retname,
                const=p_const,
                volatile=bool(p.get("volatile", 0)),
                array=p.get("array"),
                refs=p_reference,
                pointers=p_pointer,
            )

            x_all_params.append(pctx)
            if not po.ignore:
                x_filtered_params.append(pctx)
                if ptype == "out":
                    need_lambda = True
                    out_params.append(pctx)
                    x_temps.append(pctx)

                elif ptype == "in":
                    x_in_params.append(pctx)

                elif ptype == "tmp":
                    x_temps.append(pctx)

        if buffer_params:
            raise ValueError(
                "incorrect buffer param names '%s'"
                % ("', '".join(buffer_params.keys()))
            )

        x_return_value_policy = _rvp_map[data.return_value_policy]

        # Set up the function's name
        if data.rename:
            # user preference wins, of course
            py_name = data.rename
        elif fn["constructor"]:
            py_name = "__init__"
        else:
            # Python exposed function name converted to camelcase
            py_name = self._make_py_name(
                fn["name"], data, is_operator=fn.get("operator", False)
            )
            if not py_name[:2].isupper():
                py_name = f"{py_name[0].lower()}{py_name[1:]}"

            if data.internal or internal:
                py_name = f"_{py_name}"

        doc_quoted = self._process_doc(fn, data, param_remap=param_remap)

        # Allow the user to override our auto-detected keepalives
        if data.keepalive is not None:
            keepalives = data.keepalive

        ref_qualifiers = fn.get("ref_qualifiers", "")

        if not self.report_only:
            if fn["template"]:
                if data.template_impls is None and not data.cpp_code:
                    raise ValueError(
                        f"{fn['name']}: must specify template impls for function template"
                    )
            else:
                if data.template_impls is not None:
                    raise ValueError(
                        f"{fn['name']}: cannot specify template_impls for non-template functions"
                    )

            if data.ignore_pure and not fn["pure_virtual"]:
                raise ValueError(
                    f"{fn['name']}: cannot specify ignore_pure for function that isn't pure"
                )

            if data.trampoline_cpp_code and (not fn["override"] and not fn["virtual"]):
                raise ValueError(
                    f"{fn['name']}: cannot specify trampoline_cpp_code for a non-virtual method"
                )

            if data.virtual_xform and (not fn["override"] and not fn["virtual"]):
                raise ValueError(
                    f"{fn['name']}: cannot specify virtual_xform for a non-virtual method"
                )

            if ref_qualifiers == "&&":
                # pybind11 doesn't support this, user must fix it
                if not data.ignore_py and not data.cpp_code:
                    raise ValueError(
                        f"{fn['name']}: has && ref-qualifier which cannot be directly bound by pybind11, must specify cpp_code or ignore_py"
                    )

        #
        # fn_retval is needed for gensig, vcheck assertions
        # - gensig is not computable here
        #
        fn_retval: typing.Optional[str] = None
        if not is_constructor:
            # rtnType and returns are inconsistent in CppHeaderParser's output
            # because sometimes it resolves them, so just do our best for now

            self._add_type_caster(fn["returns"])

            retval = []
            if fn.get("returns_const"):
                retval.append("const")
            if "returns_enum" in fn:
                retval.append(fn["rtnType"])
            else:
                retval.append(fn["returns"])
            if fn["returns_pointer"]:
                retval.append("*")
            if fn["returns_reference"]:
                retval.append("&")
            fn_retval = " ".join(retval)

        # Lambda generation:
        # - in_params (needed for py::arg generation)
        # - x_lambda stuff
        if need_lambda:
            call_start = ""
            lambda_ret = ""

            # Return all out parameters
            x_rets.extend(out_params)

            if fn_retval != "void":
                call_start = "auto __ret ="
                x_rets.insert(
                    0, _ReturnParamContext(cpp_retname="__ret", cpp_type=fn_retval)
                )

            if len(x_rets) == 1 and x_rets[0].cpp_type != "void":
                lambda_ret = f"return {x_rets[0].cpp_retname};"
            elif len(x_rets) > 1:
                lambda_ret = "return std::make_tuple(%s);" % ",".join(
                    [p.cpp_retname for p in x_rets]
                )

            # Temporary values to store out parameters in
            if x_temps:
                for out in reversed(x_temps):
                    odef = out.default
                    if not odef:
                        lambda_pre.insert(0, f"{out.cpp_type} {out.arg_name}")
                    elif odef.startswith("{"):
                        lambda_pre.insert(0, f"{out.cpp_type} {out.arg_name}{odef}")
                    else:
                        lambda_pre.insert(0, f"{out.cpp_type} {out.arg_name} = {odef}")

            pre = _lambda_predent + f";\n{_lambda_predent}".join(lambda_pre) + ";"

            genlambda = GeneratedLambda(
                pre=pre,
                call_start=call_start,
                ret=lambda_ret,
                in_params=x_in_params,
                out_params=out_params,
            )

        return FunctionContext(
            cpp_name=fn["name"],
            doc=doc_quoted,
            scope_var=scope_var,
            # transforms
            py_name=py_name,
            cpp_return_type=fn_retval,
            all_params=x_all_params,
            filtered_params=x_filtered_params,
            has_buffers=has_buffers,
            keepalives=keepalives,
            return_value_policy=x_return_value_policy,
            # lambda generation
            genlambda=genlambda,
            # info
            const=fn["const"],
            vararg=fn["vararg"],
            ref_qualifiers=ref_qualifiers,
            is_constructor=is_constructor,
            # user settings
            ignore_pure=data.ignore_pure,
            ignore_py=data.ignore_py,
            cpp_code=data.cpp_code,
            trampoline_cpp_code=data.trampoline_cpp_code,
            ifdef=data.ifdef,
            ifndef=data.ifndef,
            release_gil=not data.no_release_gil,
            template_impls=data.template_impls,
            virtual_xform=data.virtual_xform,
            is_overloaded=overload_tracker,
        )

    def function_hook(self, fn, h2w_data):
        # operators that aren't class members aren't rendered
        if fn.get("operator"):
            return

        signature = self._get_function_signature(fn)
        data, overload_tracker = self.gendata.get_function_data(fn["name"], signature)
        if data.ignore:
            return

        scope_var = self._get_module_var(data)
        fctx = self._function_hook(fn, data, scope_var, False, overload_tracker)
        fctx.namespace = fn["namespace"]
        self.hctx.functions.append(fctx)

    def class_hook(self, cls, h2w_data):
        # ignore private classes
        if cls["parent"] is not None and cls["access_in_parent"] == "private":
            return

        cls_name = cls["name"]
        cls_key = cls_name
        c = cls
        while c["parent"]:
            c = c["parent"]
            cls_key = c["name"] + "::" + cls_key

        class_data = self.gendata.get_class_data(cls_key)

        if class_data.ignore:
            return

        for _, u in cls["using"].items():
            self._add_type_caster(u["raw_type"])

        for typename in class_data.force_type_casters:
            self._add_type_caster(typename)

        scope_var = self._get_module_var(class_data)
        var_name = f"cls_{cls_name}"

        # No template stuff
        simple_cls_qualname = f'{cls["namespace"]}::{cls_name}'

        # Template stuff
        parent_ctx: typing.Optional[ClassContext] = None
        if cls["parent"]:
            parent_ctx: ClassContext = cls["parent"]["class_ctx"]
            cls_qualname = f"{parent_ctx.full_cpp_name}::{cls_name}"
            scope_var = parent_ctx.var_name
        else:
            cls_qualname = simple_cls_qualname

        cls_cpp_identifier = cls_qualname.translate(self._qualname_trans)

        enums: typing.List[EnumContext] = []
        unnamed_enums: typing.List[EnumContext] = []

        # fix enum paths
        for i, e in enumerate(cls["enums"]["public"]):
            enum_data = self.gendata.get_cls_enum_data(
                e.get("name"), cls_key, class_data
            )
            if not enum_data.ignore:
                scope = f"{cls_qualname}::"
                enum_var_name = f"{var_name}_enum{i}"
                ectx = self._enum_hook(scope, var_name, enum_var_name, e, enum_data)
                if ectx.full_cpp_name:
                    enums.append(ectx)
                else:
                    unnamed_enums.append(ectx)

        # update inheritance

        pybase_params = set()
        bases: typing.List[BaseClassData] = []
        ignored_bases = {ib: True for ib in class_data.ignored_bases}

        for base in cls["inherits"]:
            if ignored_bases.pop(base["class"], None) or base["access"] == "private":
                continue

            bqual = class_data.base_qualnames.get(base["decl_name"])
            if bqual:
                full_cpp_name_w_templates = bqual
                # TODO: sometimes need to add this to pybase_params, but
                # that would require parsing this more. Seems sufficiently
                # obscure, going to omit it for now.
                tp = bqual.find("<")
                if tp == -1:
                    base_full_cpp_name = bqual
                    template_params = ""
                else:
                    base_full_cpp_name = bqual[:tp]
                    template_params = bqual[tp + 1 : -1]
            else:
                if "::" not in base["decl_name"]:
                    base_full_cpp_name = f'{cls["namespace"]}::{base["decl_name"]}'
                else:
                    base_full_cpp_name = base["decl_name"]

                base_decl_params = base.get("decl_params")
                if base_decl_params:
                    template_params = self._make_base_params(
                        base_decl_params, pybase_params
                    )
                    full_cpp_name_w_templates = (
                        f"{base_full_cpp_name}<{template_params}>"
                    )
                else:
                    template_params = ""
                    full_cpp_name_w_templates = base_full_cpp_name

            base_identifier = base_full_cpp_name.translate(self._qualname_trans)

            bases.append(
                BaseClassData(
                    full_cpp_name=base_full_cpp_name,
                    full_cpp_name_w_templates=full_cpp_name_w_templates,
                    full_cpp_name_identifier=base_identifier,
                    template_params=template_params,
                )
            )

        if not self.report_only and ignored_bases:
            bases = ", ".join(base["class"] for base in cls["inherits"])
            invalid_bases = ", ".join(ignored_bases.keys())
            raise ValueError(
                f"{cls_name}: ignored_bases contains non-existant bases "
                + f"{invalid_bases}; valid bases are {bases}"
            )

        self.hctx.class_hierarchy[simple_cls_qualname] = [
            base.full_cpp_name for base in bases
        ] + class_data.force_depends

        # <N, .. >
        template_argument_list = ""
        # <typename N, .. >
        template_parameter_list = ""

        template_data: typing.Optional[ClassTemplateData] = None

        if class_data.template_params:
            if class_data.subpackage:
                raise ValueError(
                    f"{cls_name}: classes with subpackages must define subpackage on template instantiation"
                )

            template_args = []
            template_params = []

            base_template_args = []
            base_template_params = []

            for param in class_data.template_params:
                if " " in param:
                    arg = param.split(" ", 1)[1]
                else:
                    arg = param
                    param = f"typename {param}"

                template_args.append(arg)
                template_params.append(param)

                if arg in pybase_params:
                    base_template_args.append(arg)
                    base_template_params.append(param)

            template_argument_list = ", ".join(template_args)
            template_parameter_list = ", ".join(template_params)

            template_data = ClassTemplateData(
                parameter_list=template_parameter_list,
                inline_code=class_data.template_inline_code,
            )

            cls_qualname = f"{cls_qualname}<{template_argument_list}>"
        else:
            base_template_params = None
            base_template_args = None

        if not self.report_only:
            if "template" in cls:
                if template_parameter_list == "":
                    raise ValueError(
                        f"{cls_name}: must specify template_params for templated class, or ignore it"
                    )
            else:
                if template_parameter_list != "":
                    raise ValueError(
                        f"{cls_name}: cannot specify template_params for non-template class"
                    )

        has_constructor = False
        is_polymorphic = class_data.is_polymorphic
        vcheck_fns: typing.List[FunctionContext] = []

        # bad assumption? yep
        if cls["inherits"]:
            is_polymorphic = True

        # Accumulate methods into various lists used by the generator templates

        wrapped_public_methods: typing.List[FunctionContext] = []
        wrapped_protected_methods: typing.List[FunctionContext] = []

        # This is:

        # - methods.public + cls.methods.protected if fn.final
        # - cls.methods.private if fn.final or fn.override
        methods_to_disable: typing.List[FunctionContext] = []
        protected_constructors: typing.List[FunctionContext] = []
        virtual_methods: typing.List[FunctionContext] = []
        non_virtual_protected_methods: typing.List[FunctionContext] = []

        for access, methods in (
            ("public", wrapped_public_methods),
            ("protected", wrapped_protected_methods),
            ("private", []),
        ):
            for fn in cls["methods"][access]:
                is_constructor = fn["constructor"]
                is_override = fn["override"]
                is_virtual = fn["virtual"] or is_override

                has_constructor |= is_constructor
                is_polymorphic |= is_virtual

                operator = fn.get("operator")

                # Ignore some operators, move constructors, copy constructors
                if (
                    (operator and operator not in _operators)
                    or fn.get("destructor")
                    or (
                        is_constructor
                        and fn["parameters"]
                        and fn["parameters"][0]["class"] is cls
                    )
                    or fn["deleted"]
                ):
                    continue

                is_final = fn["final"]
                is_private = access == "private"

                # this has to be done even on private functions, because
                # we do overload detection here
                signature = self._get_function_signature(fn)
                method_data, overload_tracker = self.gendata.get_function_data(
                    fn["name"], signature, cls_key, class_data, is_private
                )

                # Have to process private virtual functions too
                if not is_private or is_virtual or is_final:
                    if method_data.ignore:
                        continue

                    if operator:
                        self.hctx.need_operators_h = True
                        if method_data.no_release_gil is None:
                            method_data.no_release_gil = True

                    internal = access != "public"

                    try:
                        fctx = self._function_hook(
                            fn,
                            method_data,
                            var_name,
                            internal,
                            overload_tracker,
                        )
                    except Exception as e:
                        raise HookError(f"{cls_key}::{fn['name']}") from e

                    # Update class-specific method attributes
                    if operator:
                        fctx.operator = operator

                    if fn["static"]:
                        fctx.is_static_method = True

                    if fn["pure_virtual"]:
                        fctx.is_pure_virtual = True

                    # Update method lists
                    if is_private and is_override:
                        methods_to_disable.append(fctx)
                    else:
                        if is_final:
                            methods_to_disable.append(fctx)

                        # disable virtual method generation for functions with buffer
                        # parameters (doing it correctly is hard, so we skip it)
                        if is_virtual and not fctx.has_buffers:
                            virtual_methods.append(fctx)

                        if not is_private:
                            if not fctx.ignore_py:
                                methods.append(fctx)

                            if access == "protected":
                                if is_constructor:
                                    protected_constructors.append(fctx)
                                elif not is_virtual:
                                    non_virtual_protected_methods.append(fctx)

                    # If the method has cpp_code defined, it must either match the function
                    # signature of the method, or virtual_xform must be defined with an
                    # appropriate conversion. If neither of these are true, it will lead
                    # to difficult to diagnose errors at runtime. We add a static assert
                    # to try and catch these errors at compile time
                    need_vcheck = (
                        is_virtual
                        and method_data.cpp_code
                        and not method_data.virtual_xform
                        and not method_data.trampoline_cpp_code
                        and not cls["final"]
                        and not class_data.force_no_trampoline
                    )
                    if need_vcheck:
                        vcheck_fns.append(fctx)
                        self.hctx.has_vcheck = True

        # If there isn't already a constructor, add a default constructor
        # - was going to add a FunctionContext for it, but.. that's challenging
        add_default_constructor = (
            not has_constructor
            and not class_data.nodelete
            and not class_data.force_no_default_constructor
        )

        has_trampoline = (
            is_polymorphic and not cls["final"] and not class_data.force_no_trampoline
        )

        public_properties: typing.List[PropContext] = []
        protected_properties: typing.List[PropContext] = []

        for access, props in (
            ("public", public_properties),
            ("protected", protected_properties),
        ):
            # cannot bind protected properties without a trampoline, so
            # don't bother processing them if there isn't one
            if access == "protected" and not has_trampoline:
                continue

            # class attributes
            for v in cls["properties"][access]:
                prop_name = v["name"]
                propdata = self.gendata.get_cls_prop_data(
                    prop_name, cls_key, class_data
                )
                if propdata.ignore:
                    continue
                self._add_type_caster(v["raw_type"])
                if propdata.rename:
                    prop_name = propdata.rename
                else:
                    prop_name = v["name"] if access == "public" else "_" + v["name"]

                if propdata.access == PropAccess.AUTOMATIC:
                    # const variables can't be written
                    if v["constant"] or v["constexpr"]:
                        prop_readonly = True
                    # We assume that a struct intentionally has readwrite data
                    # attributes regardless of type
                    elif cls["declaration_method"] != "class":
                        prop_readonly = False
                    else:
                        # Properties that aren't fundamental or a reference are readonly unless
                        # overridden by the hook configuration
                        prop_readonly = not v["fundamental"] and not v["reference"]
                elif propdata.access == PropAccess.READONLY:
                    prop_readonly = True
                else:
                    prop_readonly = False

                doc = self._process_doc(v, propdata)

                props.append(
                    PropContext(
                        py_name=prop_name,
                        cpp_name=v["name"],
                        cpp_type=v["type"],
                        readonly=prop_readonly,
                        doc=doc,
                        array_size=v.get("array_size", None),
                        array=v["array"],
                        reference=v["reference"],
                        static=v["static"],
                    )
                )

        tctx: typing.Optional[TrampolineData] = None

        if has_trampoline:
            tmpl = ""
            if template_argument_list:
                tmpl = f", {template_argument_list}"

            trampoline_cfg = f"rpygen::PyTrampolineCfg_{cls_cpp_identifier}<{template_argument_list}>"
            tname = f"rpygen::PyTrampoline_{cls_cpp_identifier}<typename {cls_qualname}{tmpl}, typename {trampoline_cfg}>"
            tvar = f"{cls_name}_Trampoline"

            if base_template_params:
                tmpl_args = ", ".join(base_template_args)
                tmpl_params = ", ".join(base_template_params)
            else:
                tmpl_args = ""
                tmpl_params = ""

            tctx = TrampolineData(
                full_cpp_name=tname,
                var=tvar,
                inline_code=class_data.trampoline_inline_code,
                tmpl_args=tmpl_args,
                tmpl_params=tmpl_params,
                methods_to_disable=methods_to_disable,
                virtual_methods=virtual_methods,
                protected_constructors=protected_constructors,
                non_virtual_protected_methods=non_virtual_protected_methods,
            )

        elif class_data.trampoline_inline_code is not None:
            raise HookError(
                f"{cls_key} has trampoline_inline_code specified, but there is no trampoline!"
            )

        # do logic for extracting user defined typealiases here
        # - these are at class scope, so they can include template
        typealias_names = set()
        user_typealias = []
        self._extract_typealias(class_data.typealias, user_typealias, typealias_names)

        # autodetect embedded using directives, but don't override anything
        # the user specifies
        # - these are in block scope, so they cannot include templates
        auto_typealias = []
        for name, using in cls["using"].items():
            if (
                using["access"] == "public"
                and name not in typealias_names
                and not using["template"]
                and using["using_type"] == "typealias"
            ):
                auto_typealias.append(
                    f"using {name} [[maybe_unused]] = typename {cls_qualname}::{name}"
                )

        doc = self._process_doc(cls, class_data)
        py_name = self._make_py_name(cls_name, class_data)

        constants = []
        for constant in class_data.constants:
            name = constant.split("::")[-1]
            constants.append((name, constant))

        cctx = ClassContext(
            parent=parent_ctx,
            namespace=cls["namespace"],
            cpp_name=cls["name"],
            full_cpp_name=cls_qualname,
            full_cpp_name_identifier=cls_cpp_identifier,
            py_name=py_name,
            scope_var=scope_var,
            var_name=var_name,
            nodelete=class_data.nodelete,
            final=cls["final"],
            doc=doc,
            bases=bases,
            trampoline=tctx,
            public_properties=public_properties,
            protected_properties=protected_properties,
            add_default_constructor=add_default_constructor,
            wrapped_public_methods=wrapped_public_methods,
            wrapped_protected_methods=wrapped_protected_methods,
            enums=enums,
            unnamed_enums=unnamed_enums,
            template=template_data,
            auto_typealias=auto_typealias,
            vcheck_fns=vcheck_fns,
            user_typealias=user_typealias,
            constants=constants,
            inline_code=class_data.inline_code or "",
            force_multiple_inheritance=class_data.force_multiple_inheritance,
        )

        # store this to facilitate finding data in parent
        cls["class_ctx"] = cctx

        if cctx.parent:
            cctx.parent.child_classes.append(cctx)
        else:
            self.hctx.classes.append(cctx)
        if cctx.trampoline:
            self.hctx.classes_with_trampolines.append(cctx)
