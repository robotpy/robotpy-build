"""
    Header2Whatever hooks used for generating C++ wrappers
"""

import sphinxify


_missing = object()


def header_hook(header, data):
    """Called for each header"""

    for e in header.enums:
        e["x_namespace"] = e["namespace"]


def public_method_hook(fn, data):
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
        fn["data"] = {"ignore": True}
        return

    # Python exposed function name converted to camelcase
    x_name = fn["name"]
    sp = data.get("strip_prefixes")
    if sp:
        for pfx in sp:
            if x_name.startswith(pfx):
                x_name = x_name[len(pfx) :]
                break

    x_name = x_name[0].lower() + x_name[1:]

    x_in_params = []
    x_out_params = []
    x_rets = []

    data = data.get(fn["name"], _missing)
    if data is _missing:
        # ensure every function is in our yaml
        if "parent" in fn:
            print("WARNING:", fn["parent"]["name"], "method", fn["name"], "missing")
        else:
            print("WARNING: function", fn["name"], "missing")
        data = {}
        # assert False, fn['name']
    elif data is None:
        data = {}

    if "overloads" in data:
        _sig = ", ".join(
            p.get("enum", p["raw_type"]) + "&" * p["reference"] + "*" * p["pointer"]
            for p in fn["parameters"]
        )
        if _sig in data["overloads"]:
            data = data.copy()
            overload = data["overloads"][_sig]
            if overload:
                data.update(overload)
        else:
            print(
                "WARNING: Missing overload %s::%s(%s)"
                % (fn["parent"]["name"], fn["name"], _sig)
            )

    # Use this if one of the parameter types don't quite match
    param_override = data.get("param_override", {})

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

        if p["name"] in param_override:
            p.update(param_override[p["name"]])

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

    if "return" in data.get("code", ""):
        raise ValueError("%s: Do not use return, assign to retval instead" % fn["name"])

    # Rename internal functions
    if data.get("internal", False):
        x_name = "_" + x_name
    elif data.get("rename", False):
        x_name = data["rename"]
    elif fn["constructor"]:
        x_name = "__init__"

    doc = ""
    doc_quoted = ""

    if "doc" in data:
        doc = data["doc"]
    elif "doxygen" in fn:
        # work around a CppHeaderParser bug
        doc = fn["doxygen"].rpartition("*//*")[2]
        doc = sphinxify.process_raw(doc)

    if "Global default" in doc:
        doc = ""

    if doc:
        # TODO
        doc = doc.replace("\\", "\\\\").replace('"', '\\"')
        doc_quoted = doc.splitlines(keepends=True)
        doc_quoted = ['"%s"' % (dq.replace("\n", "\\n"),) for dq in doc_quoted]

    if "hook" in data:
        eval(data["hook"])(fn, data)

    name = fn["name"]
    hascode = "code" in data or "get" in data or "set" in data

    # lazy :)
    fn.update(locals())


def function_hook(fn, data):
    data = data.get("data", {})
    data = data.get("functions", {})
    public_method_hook(fn, data)


def class_hook(cls, data):

    # work around CppHeaderParser hoisting structs nested in classes to top
    if cls["parent"] is not None:
        cls["data"] = {"ignore": True}
        return

    data = data.get("data", {})
    data = data.get(cls["name"])
    if data is None:
        print("WARNING: class", cls["name"], "missing")
        data = {}

    # fix enum paths
    for e in cls["enums"]["public"]:
        e["x_namespace"] = e["namespace"] + "::" + cls["name"] + "::"

    cls["data"] = data
    methods_data = data.get("methods", {})
    for fn in cls["methods"]["public"]:
        public_method_hook(fn, methods_data)
