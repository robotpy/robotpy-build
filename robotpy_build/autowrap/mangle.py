import typing

from .j2_context import FunctionContext
from cxxheaderparser.types import (
    Array,
    DecoratedType,
    FunctionType,
    FundamentalSpecifier,
    Method,
    MoveReference,
    NameSpecifier,
    Pointer,
    Reference,
    Type,
)

# yes, we include some stdint types in here, but that's fine, this
# is just a best effort generator
_builtins = {
    "void": "v",
    "wchar_t": "w",
    "bool": "b",
    "char": "c",
    "signed char": "a",
    "int8_t": "a",
    "unsigned char": "h",
    "uint8_t": "c",
    "short": "s",
    "int16_t": "s",
    "unsigned short": "t",
    "uint16_t": "t",
    "int": "i",
    "int32_t": "i",
    "unsigned int": "j",
    "uint32_t": "j",
    "long": "l",
    "unsigned long": "m",
    "long long": "x",
    "__int64": "x",
    "int64_t": "x",
    "unsigned long long": "y",
    "unsigned __int64": "y",
    "uint64_t": "y",
    "__int128": "n",
    "unsigned __int128": "o",
    "float": "f",
    "double": "d",
    "long double": "e",
    "__float128": "g",
    "char32_t": "Di",
    "char16_t": "Ds",
    "auto": "Da",
}

_type_bad_chars = ":<>=()&,"
_type_trans = str.maketrans(_type_bad_chars, "_" * len(_type_bad_chars))


def _encode_type(dt: DecoratedType, names: typing.List[str]) -> str:
    # Decode the type
    ptrs = 0
    refs = 0
    const = False
    volatile = False

    t = dt
    while True:
        if isinstance(t, Type):
            const = const or t.const
            volatile = volatile or t.volatile
            break
        elif isinstance(t, Pointer):
            ptrs += 1
            const = const or t.const
            volatile = volatile or t.volatile
            t = t.ptr_to
        elif isinstance(t, Reference):
            refs += 1
            t = t.ref_to
        elif isinstance(t, MoveReference):
            refs += 2
            t = t.moveref_to
        else:
            break

    # prefix with cv-qualifiers, refs, pointers
    if const:
        names.append("K")
    if volatile:
        names.append("V")

    if isinstance(t, Array):
        assert False  # TODO, convert array size?
        names.append("A" * t.size)

    if refs == 1:
        names.append("R")
    elif refs == 2:
        names.append("O")

    if ptrs:
        names.append("P" * ptrs)

    if isinstance(t, FunctionType):
        # encode like a function but include the return type
        names.append("F")
        _encode_type(t.return_type, names)
        params = t.parameters
        if not params:
            names.append("_v")
        else:
            for p in params:
                names.append("_")
                _encode_type(p.type, names)
        if t.vararg:
            names.append("_z")
    else:
        typename = t.typename.segments[-1]
        if isinstance(typename, (FundamentalSpecifier, NameSpecifier)):
            typ = _builtins.get(typename.name)
            if not typ:
                # .. good enough, there are cases where this would fail, but
                # hopefully that doesn't happen?
                typ = f"T{typename.name.translate(_type_trans)}"
        else:
            typ = "T__"

        names.append(typ)


def trampoline_signature(fctx: FunctionContext) -> str:
    """
    In our trampoline functions, each function can be disabled by defining
    a macro corresponding to the function type. This helper function
    generates a mangled name based on the function name and types.

    This is roughly based on the IA64 name mangling scheme that GCC uses,
    but omits template stuff.

    function name
    cv qualifiers
    parameter types
    """

    # fast path in case it was computed previously
    if fctx._trampoline_signature:
        return fctx._trampoline_signature

    # TODO: operator overloads
    names = []

    fn = fctx._fn
    if isinstance(fn, Method):
        if fn.const:
            names.append("K")
        refqual = fn.ref_qualifier
        if refqual:
            if refqual == "&":
                names.append("R")
            if refqual == "&&":
                names.append("O")

    names.append(fctx.cpp_name)

    params = fn.parameters
    if not params:
        names.append("_v")
    else:
        for p in params:
            names.append("_")
            _encode_type(p.type, names)

    if fn.vararg:
        names.append("_z")

    fctx._trampoline_signature = "".join(names)
    return fctx._trampoline_signature
