"""
    Header2Whatever hooks used for generating C++ wrappers
"""

import sphinxify

# terrible hack
__name__ = "robotpy_build.hooks"
from .hooks_datacfg import ClassData, FunctionData, MethodData


_missing = object()


class HookError(Exception):
    pass


def header_hook(header, data):
    """Called for each header"""

    for e in header.enums:
        e["x_namespace"] = e["namespace"]


def _function_hook(fn, global_data, fn_data, typ):
    """shared with methods/functions"""

    # Ignore operators, move constructors, copy constructors
    if (
        fn["name"].startswith("operator")
        or fn.get("destructor")
        or (
            fn.get("constructor")
            and fn["parameters"]
            and fn["parameters"][0]["name"] == "&"
        )
    ):
        fn["data"] = typ({"ignore": True})
        return

    # Python exposed function name converted to camelcase
    x_name = fn["name"]
    sp = global_data.strip_prefixes
    if sp:
        for pfx in sp:
            if x_name.startswith(pfx):
                x_name = x_name[len(pfx) :]
                break

    x_name = x_name[0].lower() + x_name[1:]

    x_in_params = []
    x_out_params = []
    x_rets = []

    data = fn_data.get(fn["name"], _missing)
    if data is _missing:
        # ensure every function is in our yaml so someone can review it
        if "parent" in fn:
            print("WARNING:", fn["parent"]["name"], "method", fn["name"], "missing")
        else:
            print("WARNING: function", fn["name"], "missing")
        data = typ()
        # assert False, fn['name']
    elif data is None:
        data = typ()

    if getattr(data, "overloads", {}):
        _sig = ", ".join(
            p.get("enum", p["raw_type"]) + "&" * p["reference"] + "*" * p["pointer"]
            for p in fn["parameters"]
        )
        if _sig in data.overloads:
            overload = data.overloads[_sig]
            if overload:
                data = data.to_native()
                data.update(overload.to_native())
                data = typ(data)
        else:
            print(
                "WARNING: Missing overload %s::%s(%s)"
                % (fn["parent"]["name"], fn["name"], _sig)
            )

    # Use this if one of the parameter types don't quite match
    param_override = data.param_override

    # fix cppheaderparser quirk
    if len(fn["parameters"]) == 1:
        p = fn["parameters"][0]
        if p["type"] == "void" and not p["pointer"]:
            fn["parameters"] = []

    for i, p in enumerate(fn["parameters"]):
        if p["name"] == "":
            p["name"] = "param%s" % i
        p["x_type"] = p.get("enum", p["raw_type"])
        p["x_callname"] = p["name"]

        if "forward_declared" in p:
            fn["forward_declare"] = True
            if "parent" in fn:
                fn["parent"]["has_fwd_declare"] = True

        po = param_override.get(p["name"])
        if po:
            p.update(po.to_native())

        p["x_pyarg"] = 'py::arg("%(name)s")' % p

        if "default" in p:
            p["default"] = str(p["default"])
            p["x_pyarg"] += "=" + p["default"]

        ptype = "in"

        if p["pointer"] and not p["constant"]:
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
        else:
            x_in_params.append(p)

        if p["constant"]:
            p["x_type"] = "const " + p["x_type"]

        p["x_type_full"] = p["x_type"]
        p["x_type_full"] += "&" * p["reference"]
        p["x_type_full"] += "*" * p["pointer"]

        p["x_decl"] = "%s %s" % (p["x_type_full"], p["name"])

    x_callstart = ""
    x_callend = ""
    x_wrap_return = ""

    # Return all out parameters
    x_rets.extend(x_out_params)

    if fn["rtnType"] != "void":
        x_callstart = "auto __ret ="
        x_rets.insert(0, dict(name="__ret", x_type=fn["rtnType"]))

    if len(x_rets) == 1 and x_rets[0]["x_type"] != "void":
        x_wrap_return = "return %s;" % x_rets[0]["name"]
    elif len(x_rets) > 1:
        x_wrap_return = "return std::make_tuple(%s);" % ",".join(
            [p["name"] for p in x_rets]
        )

    # Temporary values to store out parameters in
    x_temprefs = ""
    if x_out_params:
        x_temprefs = "; ".join(["%(x_type)s %(name)s" % p for p in x_out_params]) + ";"

    # Rename internal functions
    if data.internal:
        x_name = "_" + x_name
    elif data.rename:
        x_name = data.rename
    elif fn["constructor"]:
        x_name = "__init__"

    doc = ""
    doc_quoted = ""

    if data.doc is not None:
        doc = data.doc
    elif "doxygen" in fn:
        # work around a CppHeaderParser bug
        doc = fn["doxygen"].rpartition("*//*")[2]
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
            # lambda generation
            x_callstart=x_callstart,
            x_temprefs=x_temprefs,
            x_callend=x_callend,
            x_wrap_return=x_wrap_return,
            # docstrings
            x_doc=doc,
            x_doc_quoted=doc_quoted,
        )
    )


def function_hook(fn, data):
    global_data = data.get("data", {})
    functions_data = data.get("functions", {})
    _function_hook(fn, global_data, functions_data, FunctionData)


def class_hook(cls, data):

    # work around CppHeaderParser hoisting structs nested in classes to top
    if cls["parent"] is not None:
        cls["data"] = {"ignore": True}
        return

    global_data = data.get("data", {})
    class_data = global_data.classes.get(cls["name"])
    if class_data is None:
        print("WARNING: class", cls["name"], "missing")
        class_data = ClassData()

    # fix enum paths
    for e in cls["enums"]["public"]:
        e["x_namespace"] = e["namespace"] + "::" + cls["name"] + "::"

    cls["data"] = class_data
    methods_data = class_data.methods
    for fn in cls["methods"]["public"]:
        try:
            _function_hook(fn, global_data, methods_data, MethodData)
        except Exception as e:
            raise HookError(f"{cls['name']}::{fn['name']}") from e
