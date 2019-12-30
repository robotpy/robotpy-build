"""
    Header2Whatever hooks used for generating C++ wrappers
"""

import sphinxify
import yaml

# terrible hack
__name__ = "robotpy_build.hooks"
from .hooks_datacfg import BufferType, ClassData, FunctionData, MethodData
from .mangle import trampoline_signature

_missing = object()

# TODO: this isn't the best solution
def _gen_int_types():
    for i in ("int", "uint"):
        for j in ("", "_fast", "_least"):
            for k in ("8", "16", "32", "64"):
                yield f"{i}{j}{k}_t"
    yield "intmax_t"
    yield "uintmax_t"


_int32_types = set(_gen_int_types())


class HookError(Exception):
    pass


def _using_signature(fn):
    return f"{fn['parent']['x_qualname_']}_{fn['name']}"


def _process_fn_report(clsname, fn_report):
    # generate a structure that can be copy/pasted into the generation
    # data yaml and print it out if there's missing data

    # data is missing if either: has_data is False, or there are multiple
    # overloads and one of them is missing

    data = {}

    for fn, fndata in fn_report.items():
        overloads_count = len(fndata["overloads"])
        has_data = fndata["has_data"] and (
            overloads_count == 1 or all(fndata["overloads"].values())
        )
        if not has_data:
            if overloads_count > 1:
                data[fn] = {
                    "overloads": {
                        k: {} for k, v in fndata["overloads"].items() if not v
                    }
                }
            else:
                data[fn] = {}

    if data:
        if clsname:
            data = {"classes": {clsname: {"shared_ptr": False, "methods": data}}}
        else:
            data = {"functions": data}
        print("WARNING: some methods not in generation spec")
        print(
            yaml.safe_dump(data, sort_keys=False)
            .replace(" {}", "")
            .replace("? ''\n          :", '"":')
        )


def _strip_prefixes(global_data, name):
    sp = global_data.strip_prefixes
    if sp:
        for pfx in sp:
            if name.startswith(pfx):
                name = name[len(pfx) :]
                break

    return name


def _resolve_default(fn, name):
    if isinstance(name, (int, float)):
        return str(name)
    if name in ("NULL", "nullptr"):
        return name

    # if there's a parent, look there
    parent = fn["parent"]
    if parent:
        for prop in parent["properties"]["public"]:
            if prop["name"] == name:
                name = f"{parent['namespace']}::{parent['name']}::{name}"
    return name


def _enum_hook(en, global_data, enum_data):
    ename = en.get("name")
    value_prefix = None
    if ename:
        data = enum_data.get(ename)
        if data and data.value_prefix:
            value_prefix = data.value_prefix
        else:
            value_prefix = ename

        en["x_name"] = _strip_prefixes(global_data, ename)

    for v in en["values"]:
        name = v["name"]
        if value_prefix and name.startswith(value_prefix):
            name = name[len(value_prefix) :]
            if name[0] == "_":
                name = name[1:]
        v["x_name"] = name


def header_hook(header, data):
    """Called for each header"""
    data["trampoline_signature"] = trampoline_signature
    data["using_signature"] = _using_signature
    global_data = data.get("data", {})
    for en in header.enums:
        en["x_namespace"] = en["namespace"]
        _enum_hook(en, global_data, global_data.enums)


def _function_hook(fn, global_data, fn_data, typ, fn_report, internal=False):
    """shared with methods/functions"""

    # Ignore operators, move constructors, copy constructors
    if (
        fn.get("operator")
        or fn.get("destructor")
        or (
            fn.get("constructor")
            and fn["parameters"]
            and fn["parameters"][0]["class"]
            and fn["parameters"][0]["class"]["name"] == fn["name"]
        )
    ):
        fn["data"] = typ(ignore=True)
        return

    # Python exposed function name converted to camelcase
    x_name = _strip_prefixes(global_data, fn["name"])
    x_name = x_name[0].lower() + x_name[1:]

    x_in_params = []
    x_out_params = []
    x_rets = []
    x_temps = []

    x_genlambda = False
    x_lambda_pre = []
    x_lambda_post = []

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

    fn_report_data = fn_report.setdefault(
        fn["name"], {"has_data": False, "overloads": {}, "first": fn}
    )

    data = fn_data.get(fn["name"], _missing)
    if data is _missing:
        data = typ()
        # assert False, fn['name']
    else:
        fn_report_data["has_data"] = True
        if data is None:
            data = typ()

    has_report_overload_data = False
    if getattr(data, "overloads", {}):
        if param_sig in data.overloads:
            has_report_overload_data = True
            overload = data.overloads[param_sig]
            if overload:
                data = data.dict(exclude_unset=True)
                data.update(overload.dict(exclude_unset=True))
                data = typ(**data)

    fn_report_data["overloads"][param_sig] = has_report_overload_data
    is_overloaded = len(fn_report_data["overloads"]) > 1
    if is_overloaded:
        fn_report_data["first"]["x_overloaded"] = True

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

    for i, p in enumerate(fn["parameters"]):

        if p["raw_type"] in _int32_types:
            p["fundamental"] = True
            p["unresolved"] = False

        if p["name"] == "":
            p["name"] = "param%s" % i
        p["x_type"] = p.get("enum", p["raw_type"])
        p["x_callname"] = p["name"]
        p["x_retname"] = p["name"]

        if "forward_declared" in p:
            fn["forward_declare"] = True
            if "parent" in fn:
                fn["parent"]["has_fwd_declare"] = True

        po = param_override.get(p["name"])
        if po:
            p.update(po.dict(exclude_unset=True))

        p["x_pyarg"] = 'py::arg("%(name)s")' % p

        if "default" in p:
            p["default"] = _resolve_default(fn, p["default"])
            p["x_pyarg"] += "=" + p["default"]

        ptype = "in"

        bufinfo = buffer_params.pop(p["name"], None)
        buflen = buflen_params.pop(p["name"], None)

        if bufinfo:
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

        elif p["pointer"] and not p["constant"] and p["fundamental"]:
            p["x_callname"] = "&%(x_callname)s" % p
            ptype = "out"
        elif p["array"]:
            asz = p.get("array_size", 0)
            if asz:
                p["x_type"] = "std::array<%s, %s>" % (p["x_type"], asz)
                p["x_callname"] = "%(x_callname)s.data()" % p
            else:
                # it's a vector
                pass
            ptype = "out"

        if ptype == "out":
            x_out_params.append(p)
            x_temps.append(p)
        elif ptype == "in":
            x_in_params.append(p)

        if p["constant"]:
            p["x_type"] = "const " + p["x_type"]

        p["x_type_full"] = p["x_type"]
        p["x_type_full"] += "&" * p["reference"]
        p["x_type_full"] += "*" * p["pointer"]

        p["x_decl"] = "%s %s" % (p["x_type_full"], p["name"])

    if buffer_params:
        raise ValueError(
            "incorrect buffer param names '%s'" % ("', '".join(buffer_params.keys()))
        )

    x_callstart = ""
    x_callend = ""
    x_wrap_return = ""

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
            x_lambda_pre.insert(0, "%(x_type)s %(name)s = 0" % out)

    # Rename functions
    if data.rename:
        x_name = data.rename
    elif data.internal or internal:
        x_name = "_" + x_name
    elif fn["constructor"]:
        x_name = "__init__"

    doc = ""
    doc_quoted = ""

    if data.doc is not None:
        doc = data.doc
    elif "doxygen" in fn:
        doc = fn["doxygen"]
        doc = sphinxify.process_raw(doc)

    if doc:
        # TODO
        doc = doc.replace("\\", "\\\\").replace('"', '\\"')
        doc_quoted = doc.splitlines(keepends=True)
        doc_quoted = ['"%s"' % (dq.replace("\n", "\\n"),) for dq in doc_quoted]

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
            x_in_params=x_in_params,
            x_out_params=x_out_params,
            x_rets=x_rets,
            # other
            x_overloaded=is_overloaded,
            # lambda generation
            x_genlambda=x_genlambda,
            x_callstart=x_callstart,
            x_lambda_pre=x_lambda_pre,
            x_lambda_post=x_lambda_post,
            x_callend=x_callend,
            x_wrap_return=x_wrap_return,
            # docstrings
            x_doc=doc,
            x_doc_quoted=doc_quoted,
        )
    )


def function_hook(fn, data):
    global_data = data.get("data", {})
    functions_data = global_data.functions
    fn_report = {}
    _function_hook(fn, global_data, functions_data, FunctionData, fn_report)
    _process_fn_report(None, fn_report)


def class_hook(cls, data):

    # work around CppHeaderParser hoisting structs nested in classes to top
    if cls["parent"] is not None:
        cls["data"] = {"ignore": True}
        return

    # key: function name
    # value: {has_data=bool, overloads={ "int,int"=bool }}
    fn_report = {}

    global_data = data.get("data", {})
    class_data = global_data.classes.get(cls["name"])
    if class_data is None:
        class_data = ClassData()

    # fix enum paths
    for e in cls["enums"]["public"]:
        e["x_namespace"] = e["namespace"] + "::" + cls["name"] + "::"
        _enum_hook(e, global_data, global_data.enums)

    # update inheritance
    for base in cls["inherits"]:
        if "::" not in base["class"]:
            base["x_qualname"] = f'{cls["namespace"]}::{base["class"]}'
        else:
            base["x_qualname"] = base["class"]

        base["x_qualname_"] = base["x_qualname"].replace(":", "_")

    cls["x_inherits"] = [
        base
        for base in cls["inherits"]
        if base["class"] not in class_data.ignored_bases
    ]

    cls["x_qualname"] = cls["namespace"] + "::" + cls["name"]
    cls["x_qualname_"] = cls["x_qualname"].replace(":", "_")

    cls["data"] = class_data
    has_constructor = False
    is_polymorphic = class_data.is_polymorphic
    methods_data = class_data.methods

    # bad assumption?
    if cls["inherits"]:
        is_polymorphic = True

    for access in ("public", "protected", "private"):

        for fn in cls["methods"][access]:
            if fn["constructor"]:
                has_constructor = True
            if fn["override"] or fn["virtual"]:
                is_polymorphic = True

            if access != "private":
                internal = access != "public"
                try:
                    _function_hook(
                        fn,
                        global_data,
                        methods_data,
                        MethodData,
                        fn_report,
                        internal=internal,
                    )
                except Exception as e:
                    raise HookError(f"{cls['name']}::{fn['name']}") from e

        for v in cls["properties"][access]:
            v["x_name"] = v["name"] if access == "public" else "_" + v["name"]

    cls["x_has_trampoline"] = is_polymorphic and not cls["final"]
    cls["x_has_constructor"] = has_constructor
    cls["x_varname"] = "cls_" + cls["name"]

    _process_fn_report(cls["name"], fn_report)
