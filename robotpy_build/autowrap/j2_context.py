#
# These dataclasses hold data to be rendered by the *.j2 files in templates
#
# To simplify the templates, where possible we try to do logic in the code
# that produces this data instead of in the templates.
#
# We also prefer to copy over data from the autowrap YAML file instead of using
# those data structures directly. While there's some slight overhead added,
# this should help to keep the logic outside of the templates.
#

from dataclasses import dataclass, field
import enum
import typing

from cxxheaderparser.types import Function, PQName

from ..config.autowrap_yml import ReturnValuePolicy


Documentation = typing.Optional[typing.List[str]]


class OverloadTracker:
    """Evaluates to true if overloaded"""

    def __init__(self) -> None:
        self.overloads = 0

    def add_overload(self):
        # This only needs to count new overloads, because if there are
        # multiple instances of a function it *has* to be different or
        # the compiler would complain
        self.overloads += 1

    def __bool__(self) -> bool:
        return self.overloads > 1


@dataclass
class EnumeratorContext:
    """Render data for each enumerator"""

    #: C++ name, including namespace/classname
    full_cpp_name: str

    #: Name in python
    py_name: str

    #: Documentation
    doc: Documentation


@dataclass
class EnumContext:
    """Render data for enum"""

    #: Name of parent variable in initializer
    scope_var: str

    #: Name of variable in initializer
    var_name: str

    #: C++ name without namespace
    cpp_name: str

    #: C++ name, including namespace/classname
    full_cpp_name: str

    #: Python name
    py_name: str

    #: Enum values
    values: typing.List[EnumeratorContext]

    #: Documentation
    doc: Documentation

    #
    # Copied from user's EnumData
    #

    arithmetic: bool
    inline_code: typing.Optional[str]


class ParamCategory(enum.Enum):
    IGNORE = 0
    OUT = 1
    IN = 2
    TMP = 3


@dataclass
class ParamContext:
    """Render data for each parameter"""

    # Original argument name
    arg_name: str

    # name of type with const but no *, &
    # .. why does this have const
    cpp_type: str

    # contains 'const', &, etc
    full_cpp_type: str

    #: py::arg() for pybind11, includes default value
    py_arg: str

    #: passed to lambda
    default: typing.Optional[str]

    #: Name to pass to function when calling the original
    #: .. only used by lambda
    call_name: str

    #: Name to pass to function when generating a virtual function
    virtual_call_name: str

    #: Not used in jinja template, but is used to determine variable
    #: name when used as an out parameter
    cpp_retname: str

    #: Not used in jinja template, used for filtering
    category: ParamCategory

    # type + name, rarely used
    @property
    def decl(self) -> str:
        return f"{self.full_cpp_type} {self.arg_name}"

    # only used for operator generation, rarely used
    @property
    def cpp_type_no_const(self) -> str:
        ct = self.cpp_type
        if ct.startswith("const "):
            return ct[6:]
        return ct


@dataclass
class GeneratedLambda:
    """
    Data for generating a lambda to change the behavior of the function
    """

    pre: str
    call_start: str
    ret: str

    #: input parameters
    in_params: typing.List[ParamContext]
    #: output parameters
    out_params: typing.List[ParamContext]


@dataclass
class FunctionContext:
    """Render data for a C++ function or method"""

    #: C++ name of function
    cpp_name: str

    #: Documentation
    doc: Documentation

    #: parent variable to attach to
    scope_var: str

    #: Name in python
    py_name: str

    #: Return value as fully qualified C++ type with const/*
    cpp_return_type: typing.Optional[str]

    #: All original C++ parameters for the function
    #: -> used by trampoline signature, and trampolines
    all_params: typing.List[ParamContext]

    #: every parameter except ignored
    filtered_params: typing.List[ParamContext]

    #: Has vararg parameters
    #: -> used by trampoline signature
    # vararg: bool

    #
    # Mixed
    #

    has_buffers: bool

    keepalives: typing.List[typing.Tuple[int, int]]

    return_value_policy: str

    #
    # User settings from autowrap_yml.FunctionData
    #

    #: If True, don't wrap this, but provide a pure virtual implementation
    ignore_pure: bool

    #: If True, don't expose this function to python
    ignore_py: bool

    #: Use this code instead of the generated code
    cpp_code: typing.Optional[str]
    #: Use this code instead of the generated code in a trampoline
    trampoline_cpp_code: typing.Optional[str]

    #: Generate this in an `#ifdef`
    ifdef: typing.Optional[str]
    #: Generate this in an `#ifndef`
    ifndef: typing.Optional[str]

    release_gil: bool

    # List of template instantiations
    template_impls: typing.Optional[typing.List[typing.List[str]]]

    virtual_xform: typing.Optional[str]

    # OverloadTracker evaluates to True if there are overloads
    is_overloaded: OverloadTracker

    # Used to compute the trampoline signature
    _fn: Function

    #
    # Cached/conditionally set properties
    #

    genlambda: typing.Optional[GeneratedLambda] = None

    #: Is this a constructor?
    is_constructor: bool = False

    #: & or && qualifiers for function
    ref_qualifiers: str = ""

    #: Marked const
    const: bool = False

    is_pure_virtual: bool = False

    #: If there is a namespace associated with this function, this is it,
    #: and this ends with ::
    namespace: str = ""

    #: The operator for this method
    #: - if set, cpp_type will be filled out by the parser
    operator: typing.Optional[str] = None

    #: True if this is a static method
    is_static_method: bool = False

    # Only compute the trampoline signature once, used as cache by
    # trampoline_signature function
    _trampoline_signature: typing.Optional[str] = None


@dataclass
class PropContext:
    """
    Render data for each class property
    """

    py_name: str
    cpp_name: str
    cpp_type: str
    readonly: bool
    doc: Documentation

    array_size: typing.Optional[int]
    array: bool  # cannot sensibly autowrap an array of incomplete size
    reference: bool
    static: bool
    bitfield: bool


@dataclass
class BaseClassData:
    """
    Render data for each base that a class inherits
    """

    #: C++ name, including all known components
    full_cpp_name: str  # was x_qualname

    full_cpp_name_w_templates: str  # was x_class

    #: Translated C++ name suitable for use as an identifier. :<>= are
    #: turned into underscores.
    full_cpp_name_identifier: str  # was x_qualname_

    #: C++ name + components, no template parameters
    dep_cpp_name: str

    #: comma separated list of template parameters for this base, or empty string
    template_params: str


@dataclass
class TrampolineData:
    """
    Trampolines are classes that have the original class as a base class,
    which allows us to add additional features from python:

    * Protected method/variable access
    * Implement virtual functions from python
    """

    full_cpp_name: str
    var: str
    inline_code: typing.Optional[str]

    #: trampoline base class template types
    tmpl_args: str

    #: trampoline base class template names
    tmpl_params: str

    #
    # Lists used by trampolines so that the logic in the template is less
    # complicated
    #

    # pub + protected + final (ignore doesn't matter)
    # private + final or override (ignore doesn't matter)
    # -> to delete, only needs signature
    methods_to_disable: typing.List[FunctionContext]

    # public + protected + private
    # - if not ignore and virtual and not final and not buffers)
    virtual_methods: typing.List[FunctionContext]

    # protected + not ignore + constructor
    protected_constructors: typing.List[FunctionContext]

    # protected + not (ignore or virtual or constructor)
    non_virtual_protected_methods: typing.List[FunctionContext]


@dataclass
class ClassTemplateData:
    #: N, ..
    argument_list: str
    #: <typename N, .. >
    parameter_list: str

    #: the specified C++ code is inserted into the template definition
    inline_code: str


@dataclass
class ClassContext:
    """
    Render data for each class encountered in a header

    Available in class .j2 files as `cls`
    """

    parent: typing.Optional["ClassContext"]

    #: Namespace that this class lives in
    namespace: str

    #: C++ name (only the class)
    cpp_name: str

    #: C++ name, including namespace/classname: was: x_qualname
    full_cpp_name: str

    #: Translated C++ name suitable for use as an identifier. :<>= are
    #: turned into underscores. was: x_qualname_
    full_cpp_name_identifier: str

    #: C++ name + components, no template parameters
    dep_cpp_name: str

    #: Python name
    py_name: str

    #: Name of parent variable in initializer
    scope_var: str

    #: Name of variable in initializer. was: x_varname
    var_name: str

    #: If the object shouldn't be deleted by pybind11, use this. Disables
    #: implicit constructors.
    nodelete: bool

    #: class is final
    final: bool

    #: Documentation
    doc: Documentation

    bases: typing.List[BaseClassData]

    template: typing.Optional[ClassTemplateData]

    #
    # User specified settings copied from ClassData
    #

    #: Extra 'using' directives to insert into the trampoline and the
    #: wrapping scope
    user_typealias: typing.List[str]

    #: Extra constexpr to insert into the trampoline and wrapping scopes
    #: (name, value)
    constants: typing.List[typing.Tuple[str, str]]

    #: Extra code to insert into the class scope
    inline_code: str

    #: User specified settings
    force_multiple_inheritance: bool

    #
    # Everything else
    #

    # Not used in jinja_template
    has_constructor: bool = False
    is_polymorphic: bool = False

    #: was x_has_trampoline
    trampoline: typing.Optional[TrampolineData] = None

    #
    # Properties (member variables)
    #

    public_properties: typing.List[PropContext] = field(default_factory=list)
    protected_properties: typing.List[PropContext] = field(default_factory=list)

    #
    # Methods: the idea here is have a bunch of descriptive lists here so that
    # the j2 templates don't need logic to emit each method
    #

    #
    # Method lists for wrapping
    #

    add_default_constructor: bool = False

    # public + not (ignore_pure + ignore_py)
    wrapped_public_methods: typing.List[FunctionContext] = field(default_factory=list)

    # only if trampoline:
    # - protected + not (ignore_pure + ignore_py)
    wrapped_protected_methods: typing.List[FunctionContext] = field(
        default_factory=list
    )

    #: Public enums + unnamed enums
    enums: typing.List[EnumContext] = field(default_factory=list)
    unnamed_enums: typing.List[EnumContext] = field(default_factory=list)

    #: Extra autodetected 'using' directives
    auto_typealias: typing.List[str] = field(default_factory=list)

    #: vcheck are various static asserts that check things about the
    #: inline functions
    vcheck_fns: typing.List[FunctionContext] = field(default_factory=list)

    child_classes: typing.List["ClassContext"] = field(default_factory=list)


@dataclass
class TemplateInstanceContext:
    #: Name of parent variable in initializer
    scope_var: str

    #: Name of variable in initializer
    var_name: str

    py_name: str

    full_cpp_name_identifier: str
    binder_typename: str

    params: typing.List[str]

    header_name: str

    doc_set: Documentation
    doc_add: Documentation


@dataclass
class HeaderContext:
    """
    Globals in all .j2 files
    """

    # Name in toml
    hname: str

    extra_includes_first: typing.List[str]
    extra_includes: typing.List[str]
    inline_code: typing.Optional[str]

    trampoline_signature: typing.Callable[[FunctionContext], str]
    using_signature: typing.Callable[[ClassContext, FunctionContext], str]

    #: Path to the parsed header relative to some root
    rel_fname: str

    #: True if <pybind11/operators.h> is needed
    need_operators_h: bool = False

    using_declarations: typing.List[PQName] = field(default_factory=list)

    # TODO: anon enums?
    enums: typing.List[EnumContext] = field(default_factory=list)

    # classes that are not contained in other classes
    classes: typing.List[ClassContext] = field(default_factory=list)

    # same as classes, but only those that have trampolines
    classes_with_trampolines: typing.List[ClassContext] = field(default_factory=list)

    functions: typing.List[FunctionContext] = field(default_factory=list)

    # trampolines

    # template_classes
    template_instances: typing.List[TemplateInstanceContext] = field(
        default_factory=list
    )

    type_caster_includes: typing.List[str] = field(default_factory=list)
    user_typealias: typing.List[str] = field(default_factory=list)

    using_ns: typing.List[str] = field(default_factory=list)

    # All namespaces that occur in the file
    namespaces: typing.List[str] = field(default_factory=list)

    subpackages: typing.Dict[str, str] = field(default_factory=dict)

    # key: class name, value: list of classes this class depends on
    class_hierarchy: typing.Dict[str, typing.List[str]] = field(default_factory=dict)

    has_vcheck: bool = False
