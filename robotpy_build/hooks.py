from keyword import iskeyword
import re
import sphinxify
import typing

from .hooks_datacfg import (
    HooksDataYaml,
    BufferType,
    ClassData,
    EnumValue,
    FunctionData,
    PropData,
    PropAccess,
    ReturnValuePolicy,
)
from .generator_data import GeneratorData, MissingReporter
from .mangle import trampoline_signature


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


class HookError(Exception):
    pass


def _using_signature(fn):
    return f"{fn['parent']['x_qualname_']}_{fn['name']}"


class Hooks:
    """
    Header2Whatever hooks used for generating C++ wrappers
    """

    _qualname_bad = ":<>="
    _qualname_trans = str.maketrans(_qualname_bad, "_" * len(_qualname_bad))

    def __init__(
        self,
        data: HooksDataYaml,
        casters: typing.Dict[str, typing.Dict[str, typing.Any]],
        report_only: bool,
    ):
        self.gendata = GeneratorData(data)
        self.rawdata = data
        self.casters = casters
        self.report_only = report_only
        self.has_operators = False

        self.types: typing.Set[str] = set()
        self.class_hierarchy: typing.Dict[str, typing.List[str]] = {}

        self.subpackages: typing.Dict[str, str] = {}

    def report_missing(self, name: str, reporter: MissingReporter):
        self.gendata.report_missing(name, reporter)

    def _add_type_caster(self, typename: str):
        # defer until the end since there's lots of duplication
        self.types.add(typename)

    def _add_subpackage(self, v, data):
        if data.subpackage:
            var = "pkg_" + data.subpackage.replace(".", "_")
            self.subpackages[data.subpackage] = var
            v["x_module_var"] = var
        else:
            v["x_module_var"] = "m"

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

    def _set_name(self, name, data, strip_prefixes=None, is_operator=False):
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
        self, thing, data, append_prefix=""
    ) -> typing.Optional[typing.List[str]]:
        doc = ""

        if data.doc is not None:
            doc = data.doc
        elif "doxygen" in thing:
            doc = thing["doxygen"]
            doc = sphinxify.process_raw(doc)

        if data.doc_append is not None:
            doc += f"\n{append_prefix}" + data.doc_append.replace(
                "\n", f"\n{append_prefix}"
            )

        return self._quote_doc(doc)

    def _quote_doc(
        self, doc: typing.Optional[str]
    ) -> typing.Optional[typing.List[str]]:
        doc_quoted: typing.Optional[typing.List[str]] = None
        if doc:
            # TODO
            doc = doc.replace("\\", "\\\\").replace('"', '\\"')
            doc_quoted = doc.splitlines(keepends=True)
            doc_quoted = ['"%s"' % (dq.replace("\n", "\\n"),) for dq in doc_quoted]

        return doc_quoted

    def _resolve_default(self, fn, p, name):
        if isinstance(name, (int, float)):
            return str(name)
        if name in ("NULL", "nullptr"):
            return name

        if name and name[0] == "{" and name[-1] == "}":
            if p["array"]:
                return name
            return f"{p['x_type']}{name}"

        # if there's a parent, look there
        parent = fn["parent"]
        if parent:
            for prop in parent["properties"]["public"]:
                if prop["name"] == name:
                    name = f"{parent['namespace']}::{parent['name']}::{name}"
        return name

    def _maybe_add_default_arg_cast(self, p, name):
        if not p.get("disable_type_caster_default_cast", False):
            found_typename = None
            for ccfg in self._get_type_caster_cfgs(p["x_type"]):
                if ccfg.get("darg"):
                    if found_typename and found_typename != ccfg["typename"]:
                        raise HookError(
                            f"multiple type casters found for {p['name']} ({p['x_type']}), use disable_type_caster_default_cast"
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

    def _enum_hook(self, en, enum_data):
        ename = en.get("name")
        value_prefix = None
        if ename:
            value_prefix = enum_data.value_prefix
            if not value_prefix:
                value_prefix = ename

            en["x_name"] = self._set_name(ename, enum_data)

        en["x_doc_quoted"] = self._process_doc(en, enum_data)

        if value_prefix:
            strip_prefixes = [value_prefix + "_", value_prefix]
        else:
            strip_prefixes = []

        for v in en["values"]:
            name = v["name"]
            v_data = enum_data.values.get(name)
            if v_data is None:
                v_data = EnumValue()
            v["x_name"] = self._set_name(name, v_data, strip_prefixes)
            v["data"] = v_data
            v["x_doc_quoted"] = self._process_doc(v, v_data, append_prefix="  ")

    def header_hook(self, header, data):
        """Called for each header"""
        data["trampoline_signature"] = trampoline_signature
        data["using_signature"] = _using_signature

        for en in header.enums:
            en["x_namespace"] = en["namespace"]
            enum_data = self.gendata.get_enum_data(en.get("name"))
            en["data"] = enum_data

            self._add_subpackage(en, enum_data)
            self._enum_hook(en, enum_data)

        for v in header.variables:
            var_data = self.gendata.get_prop_data(v["name"])
            v["data"] = var_data
            self._add_type_caster(v["raw_type"])

        for _, u in header.using.items():
            self._add_type_caster(u["raw_type"])

        data["class_hierarchy"] = self.class_hierarchy
        data["subpackages"] = self.subpackages
        data["x_has_operators"] = self.has_operators

        templates = {}
        for k, tmpl_data in data["data"].templates.items():
            qualname = tmpl_data.qualname
            if "::" not in qualname:
                qualname = f"::{qualname}"
            tmpl_data_d = tmpl_data.dict()
            tmpl_data_d["x_qualname_"] = qualname.translate(self._qualname_trans)
            tmpl_data_d["x_doc_set"] = self._quote_doc(tmpl_data.doc)
            doc_add = tmpl_data.doc_append
            if doc_add:
                doc_add = f"\n{doc_add}"
            tmpl_data_d["x_doc_add"] = self._quote_doc(doc_add)
            self._add_subpackage(tmpl_data_d, tmpl_data)
            templates[k] = tmpl_data_d

            for param in tmpl_data.params:
                self._add_type_caster(param)

        data["templates"] = templates

        data["type_caster_includes"] = self._get_type_caster_includes()

    def _function_hook(self, fn, data: FunctionData, internal: bool = False):
        """shared with methods/functions"""

        # Python exposed function name converted to camelcase
        x_name = self._set_name(fn["name"], data, is_operator=fn.get("operator", False))
        if not data.rename and not x_name[:2].isupper():
            x_name = x_name[0].lower() + x_name[1:]

        # if cpp_code is specified, don't release the gil unless the user
        # specifically asks for it
        if data.no_release_gil is None:
            if data.cpp_code:
                data.no_release_gil = True

        x_in_params = []
        x_out_params = []
        x_all_params = []
        x_rets = []
        x_temps = []
        x_keepalives = []

        x_genlambda = False
        x_lambda_pre: typing.List[str] = []
        x_lambda_post: typing.List[str] = []

        # Use this if one of the parameter types don't quite match
        param_override = data.param_override

        # buffers: accepts a python object that supports the buffer protocol
        #          as input. If the buffer is an 'out' buffer, then it
        #          will request a writeable buffer. Data is written by the
        #          wrapped function to that buffer directly, and the length
        #          written (if the length is a pointer) will be returned
        buffer_params = {}
        buflen_params = {}
        if data.buffers:
            for bufinfo in data.buffers:
                if bufinfo.src == bufinfo.len:
                    raise ValueError(
                        f"buffer src({bufinfo.src}) and len({bufinfo.len}) cannot be the same"
                    )
                buffer_params[bufinfo.src] = bufinfo
                buflen_params[bufinfo.len] = bufinfo

        self._add_type_caster(fn["returns"])

        is_constructor = fn.get("constructor")

        for i, p in enumerate(fn["parameters"]):

            if is_constructor and p["reference"] == 1:
                x_keepalives.append((1, i + 2))

            if p["raw_type"] in _int32_types:
                p["fundamental"] = True
                p["unresolved"] = False

            if p["name"] == "":
                p["name"] = "param%s" % i
            p["x_type"] = p.get("enum", p["raw_type"])
            p["x_callname"] = p["name"]
            p["x_retname"] = p["name"]

            po = param_override.get(p["name"])
            if po:
                p.update(po.dict(exclude_unset=True))

            p["x_pyarg"] = 'py::arg("%(name)s")' % p

            if "default" in p:
                default = self._resolve_default(fn, p, p["default"])
                default = self._maybe_add_default_arg_cast(p, default)
                p["default"] = default
                p["x_pyarg"] += "=" + p["default"]

            ptype = "in"

            buflen = buflen_params.pop(p["name"], None)

            if p["name"] in buffer_params:
                bufinfo = buffer_params.pop(p["name"])
                x_genlambda = True
                bname = f"__{bufinfo.src}"
                p["constant"] = 1
                p["reference"] = 1
                p["pointer"] = 0

                p["x_callname"] = f"({p['x_type']}*){bname}.ptr"
                p["x_type"] = "py::buffer"

                # this doesn't seem to be true for bytearrays, which is silly
                # x_lambda_pre.append(
                #     f'if (PyBuffer_IsContiguous((Py_buffer*){p["name"]}.ptr(), \'C\') == 0) throw py::value_error("{p["name"]}: buffer must be contiguous")'
                # )

                # TODO: check for dimensions, strides, other dangerous things

                # bufinfo was validated and converted before it got here
                if bufinfo.type is BufferType.IN:
                    ptype = "in"
                    x_lambda_pre += [f"auto {bname} = {p['name']}.request(false)"]
                else:
                    ptype = "in"
                    x_lambda_pre += [f"auto {bname} = {p['name']}.request(true)"]

                x_lambda_pre += [f"{bufinfo.len} = {bname}.size * {bname}.itemsize"]

                if bufinfo.minsz:
                    x_lambda_pre.append(
                        f'if ({bufinfo.len} < {bufinfo.minsz}) throw py::value_error("{p["name"]}: minimum buffer size is {bufinfo.minsz}")'
                    )

            elif buflen:
                if p["pointer"]:
                    p["x_callname"] = f"&{buflen.len}"
                    ptype = "out"
                else:
                    # if it's not a pointer, then the called function
                    # can't communicate through it, so ignore the parameter
                    p["x_callname"] = buflen.len
                    x_temps.append(p)
                    ptype = "ignored"

            elif p.get("force_out") or (
                (p["pointer"] or p["reference"] == 1)
                and not p["constant"]
                and p["fundamental"]
            ):
                if p["pointer"]:
                    p["x_callname"] = f"&{p['x_callname']}"
                ptype = "out"
            elif p["array"]:
                asz = p.get("array_size", 0)
                if asz:
                    p["x_type"] = "std::array<%s, %s>" % (p["x_type"], asz)
                    p["x_callname"] = "%(x_callname)s.data()" % p
                    if "default" not in p:
                        p["default"] = "{}"
                else:
                    # it's a vector
                    pass
                ptype = "out"

            if p.get("ignore"):
                pass
            else:
                x_all_params.append(p)
                if ptype == "out":
                    x_out_params.append(p)
                    x_temps.append(p)
                elif ptype == "in":
                    x_in_params.append(p)

            self._add_type_caster(p["x_type"])

            if p["constant"]:
                p["x_type"] = "const " + p["x_type"]

            p["x_type_full"] = p["x_type"]
            p["x_type_full"] += "&" * p["reference"]
            p["x_type_full"] += "*" * p["pointer"]

            p["x_decl"] = "%s %s" % (p["x_type_full"], p["name"])

        if buffer_params:
            raise ValueError(
                "incorrect buffer param names '%s'"
                % ("', '".join(buffer_params.keys()))
            )

        x_callstart = ""
        x_callend = ""
        x_wrap_return = ""
        x_return_value_policy = _rvp_map[data.return_value_policy]

        if x_out_params:
            x_genlambda = True

            # Return all out parameters
            x_rets.extend(x_out_params)

        if fn["rtnType"] != "void":
            x_callstart = "auto __ret ="
            x_rets.insert(0, dict(x_retname="__ret", x_type=fn["rtnType"]))

        if len(x_rets) == 1 and x_rets[0]["x_type"] != "void":
            x_wrap_return = "return %s;" % x_rets[0]["x_retname"]
        elif len(x_rets) > 1:
            x_wrap_return = "return std::make_tuple(%s);" % ",".join(
                [p["x_retname"] for p in x_rets]
            )

        # Temporary values to store out parameters in
        if x_temps:
            for out in reversed(x_temps):
                odef = out.get("default", "0")
                x_lambda_pre.insert(0, f"{out['x_type']} {out['name']} = {odef}")

        # Rename functions
        if data.rename:
            x_name = data.rename
        elif data.internal or internal:
            x_name = "_" + x_name
        elif fn["constructor"]:
            x_name = "__init__"

        doc_quoted = self._process_doc(fn, data)

        if data.keepalive is not None:
            x_keepalives = data.keepalive

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

        # if "hook" in data:
        #     eval(data["hook"])(fn, data)

        # bind new attributes to the function definition
        # -> previously used locals(), but this is more explicit
        #    and easier to not mess up
        fn.update(
            dict(
                data=data,
                # transforms
                x_name=x_name,
                x_all_params=x_all_params,
                x_in_params=x_in_params,
                x_out_params=x_out_params,
                x_rets=x_rets,
                x_keepalives=x_keepalives,
                x_return_value_policy=x_return_value_policy,
                # lambda generation
                x_genlambda=x_genlambda,
                x_callstart=x_callstart,
                x_lambda_pre=x_lambda_pre,
                x_lambda_post=x_lambda_post,
                x_callend=x_callend,
                x_wrap_return=x_wrap_return,
                # docstrings
                x_doc_quoted=doc_quoted,
            )
        )

    def function_hook(self, fn, data):
        if fn.get("operator"):
            fn["data"] = FunctionData(ignore=True)
            return

        signature = self._get_function_signature(fn)
        data = self.gendata.get_function_data(fn, signature)
        if data.ignore:
            fn["data"] = data
            return

        self._add_subpackage(fn, data)
        self._function_hook(fn, data)

    def class_hook(self, cls, data):

        if cls["parent"] is not None and cls["access_in_parent"] == "private":
            cls["data"] = ClassData(ignore=True)
            return

        cls_name = cls["name"]
        cls_key = cls_name
        c = cls
        while c["parent"]:
            c = c["parent"]
            cls_key = c["name"] + "::" + cls_key

        class_data = self.gendata.get_class_data(cls_key)
        cls["data"] = class_data

        if class_data.ignore:
            return

        for _, u in cls["using"].items():
            self._add_type_caster(u["raw_type"])

        for typename in class_data.force_type_casters:
            self._add_type_caster(typename)

        self._add_subpackage(cls, class_data)

        # fix enum paths
        for e in cls["enums"]["public"]:
            e["x_namespace"] = e["namespace"] + "::" + cls_name + "::"
            enum_data = self.gendata.get_cls_enum_data(
                e.get("name"), cls_key, class_data
            )
            e["data"] = enum_data

            self._enum_hook(e, enum_data)

        # update inheritance

        pybase_params = set()

        for base in cls["inherits"]:
            bqual = class_data.base_qualnames.get(base["class"])
            if bqual:
                base["x_qualname"] = bqual
            elif "::" not in base["decl_name"]:
                base["x_qualname"] = f'{cls["namespace"]}::{base["decl_name"]}'
            else:
                base["x_qualname"] = base["decl_name"]

            base["x_qualname_"] = base["x_qualname"].translate(self._qualname_trans)

            base_decl_params = base.get("decl_params")
            if base_decl_params:
                for decl_param in base_decl_params:
                    pybase_params.add(decl_param["param"])
                base["x_params"] = ", ".join(
                    decl_param["param"] for decl_param in base_decl_params
                )
            else:
                base["x_params"] = ""

        ignored_bases = {ib: True for ib in class_data.ignored_bases}

        cls["x_inherits"] = [
            base
            for base in cls["inherits"]
            if not ignored_bases.pop(base["class"], None)
            and base["access"] != "private"
        ]
        if not self.report_only and ignored_bases:
            bases = ", ".join(base["class"] for base in cls["inherits"])
            invalid_bases = ", ".join(ignored_bases.keys())
            raise ValueError(
                f"{cls_name}: ignored_bases contains non-existant bases "
                + f"{invalid_bases}; valid bases are {bases}"
            )

        # No template stuff
        simple_cls_qualname = f'{cls["namespace"]}::{cls_name}'

        # Template stuff
        if cls["parent"]:
            cls_qualname = f'{cls["parent"]["x_qualname"]}::{cls_name}'
        else:
            cls_qualname = simple_cls_qualname

        cls["x_qualname_"] = cls_qualname.translate(self._qualname_trans)
        self.class_hierarchy[simple_cls_qualname] = [
            base["x_qualname"] for base in cls["x_inherits"]
        ] + class_data.force_depends

        # <N, .. >
        template_argument_list = ""
        # <typename N, .. >
        template_parameter_list = ""

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

            cls_qualname = f"{cls_qualname}<{template_argument_list}>"
        else:
            base_template_params = None
            base_template_args = None

        if base_template_params:
            cls["x_pybase_args"] = ", ".join(base_template_args)
            cls["x_pybase_params"] = ", ".join(base_template_params)
        else:
            cls["x_pybase_args"] = ""
            cls["x_pybase_params"] = ""

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

        cls["x_qualname"] = cls_qualname

        has_constructor = False
        is_polymorphic = class_data.is_polymorphic

        # bad assumption? yep
        if cls["inherits"]:
            is_polymorphic = True

        for access in ("public", "protected", "private"):

            for fn in cls["methods"][access]:
                if fn["constructor"]:
                    has_constructor = True
                if fn["override"] or fn["virtual"]:
                    is_polymorphic = True

                operator = fn.get("operator")

                # Ignore some operators, move constructors, copy constructors
                if (
                    (operator and operator not in _operators)
                    or fn.get("destructor")
                    or (
                        fn.get("constructor")
                        and fn["parameters"]
                        and fn["parameters"][0]["class"] is cls
                    )
                    or fn["deleted"]
                ):
                    fn["data"] = FunctionData(ignore=True)
                    continue

                is_private = access == "private"

                # this has to be done even on private functions, because
                # we do overload detection here
                signature = self._get_function_signature(fn)
                method_data = self.gendata.get_function_data(
                    fn, signature, cls_key, class_data, is_private
                )

                if not is_private:

                    if method_data.ignore:
                        fn["data"] = method_data
                        continue

                    if operator:
                        self.has_operators = True
                        if method_data.no_release_gil is None:
                            method_data.no_release_gil = True

                    internal = access != "public"

                    try:
                        self._function_hook(fn, method_data, internal=internal)
                    except Exception as e:
                        raise HookError(f"{cls_key}::{fn['name']}") from e

        has_trampoline = (
            is_polymorphic and not cls["final"] and not class_data.force_no_trampoline
        )
        for access in ("public", "protected", "private"):
            # class attributes
            for v in cls["properties"][access]:
                if access in "private" or (
                    access == "protected" and not has_trampoline
                ):
                    v["data"] = PropData(ignore=True)
                    continue

                prop_name = v["name"]
                propdata = self.gendata.get_cls_prop_data(
                    prop_name, cls_key, class_data
                )
                self._add_type_caster(v["raw_type"])
                v["data"] = propdata
                if propdata.rename:
                    v["x_name"] = propdata.rename
                else:
                    v["x_name"] = v["name"] if access == "public" else "_" + v["name"]

                if propdata.access == PropAccess.AUTOMATIC:
                    # We assume that a struct intentionally has readwrite data
                    # attributes regardless of type
                    if cls["declaration_method"] != "class":
                        x_readonly = False
                    else:
                        # Properties that aren't fundamental or a reference are readonly unless
                        # overridden by the hook configuration
                        x_readonly = not v["fundamental"] and not v["reference"]
                elif propdata.access == PropAccess.READONLY:
                    x_readonly = True
                else:
                    x_readonly = False

                v["x_readonly"] = x_readonly
                v["x_doc_quoted"] = self._process_doc(v, propdata)

        cls["x_has_trampoline"] = has_trampoline
        cls["x_template_parameter_list"] = template_parameter_list
        if cls["x_has_trampoline"]:
            tmpl = ""
            if template_argument_list:
                tmpl = f", {template_argument_list}"

            trampoline_cfg = f"rpygen::PyTrampolineCfg_{cls['x_qualname_']}<{template_argument_list}>"
            cls[
                "x_trampoline_name"
            ] = f"rpygen::PyTrampoline_{cls['x_qualname_']}<typename {cls_qualname}{tmpl}, typename {trampoline_cfg}>"
            cls["x_trampoline_var"] = f"{cls_name}_Trampoline"
        elif class_data.trampoline_inline_code is not None:
            raise HookError(
                f"{cls_key} has trampoline_inline_code specified, but there is no trampoline!"
            )

        cls["x_has_constructor"] = has_constructor
        cls["x_varname"] = "cls_" + cls_name
        cls["x_name"] = self._set_name(cls_name, class_data)
        cls["x_doc_quoted"] = self._process_doc(cls, class_data)
