#
# Defines data that is consumed by the header2whatever hooks/templates
# to modify the generated files
#

import dataclasses
import enum
from typing import Dict, List, Tuple, Optional, Union

import yaml

from .util import fix_yaml_dict, parse_input


@dataclasses.dataclass(frozen=True)
class ParamData:
    """Various ways to modify parameters"""

    #: Set parameter name to this
    name: Optional[str] = None

    #: Change C++ type emitted
    x_type: Optional[str] = None

    #: Default value for parameter
    default: Optional[str] = None

    #: Disable default value
    no_default: Optional[bool] = False

    #: Disallow implicit conversions from None. This defaults to True for built
    #: in types and types that are obviously std::function (does not handle all
    #: cases, in which case this should be explicitly specified)
    disable_none: Optional[bool] = None

    #: Disables a default cast caused by ``default_arg_cast``
    disable_type_caster_default_cast: bool = False

    #: Force this to be an 'out' parameter
    #:
    #: .. seealso:: :ref:`autowrap_out_params`
    #:
    force_out: bool = False

    #: Force an array size
    array_size: Optional[int] = None

    #: Ignore this parameter
    ignore: bool = False


class BufferType(str, enum.Enum):
    #: The buffer must indicate that it is readable (such as bytes, or bytearray)
    IN = "in"

    #: The buffer must indicate that it is writeable (such as a bytearray)
    OUT = "out"

    #: The buffer must indicate that it readable or writeable (such as a bytearray)
    INOUT = "inout"


@dataclasses.dataclass(frozen=True)
class BufferData:
    """
    Specify that a parameter uses the buffer protocol
    """

    #: Indicates what type of python buffer is required
    type: BufferType

    #: Name of C++ parameter that the buffer will use
    src: str

    #: Name of the C++ length parameter. An out-only parameter, it will be set
    #: to the size of the python buffer, and will be returned so the caller can
    #: determine how many bytes were written
    len: str

    #: If specified, the minimum size of the python buffer
    minsz: Optional[int] = None


class ReturnValuePolicy(enum.Enum):
    """
    See `pybind11 documentation <https://pybind11.readthedocs.io/en/stable/advanced/functions.html#return-value-policies>`_
    for what each of these values mean.
    """

    #: Reference an existing object (i.e. do not create a new copy) and take ownership.
    take_ownership = "take_ownership"

    #: Create a new copy of the returned object, which will be owned by Python.
    copy = "copy"

    #: Use std::move to move the return value contents into a new instance that will be owned by Python.
    move = "move"

    #: Reference an existing object, but do not take ownership.
    reference = "reference"

    #: Indicates that the lifetime of the return value is tied to the lifetime of a parent object
    reference_internal = "reference_internal"

    #: pybind11 determines the policy to use
    automatic = "automatic"

    #: pybind11 determines the policy to use, but falls back to a reference
    automatic_reference = "automatic_reference"


@dataclasses.dataclass(frozen=True)
class OverloadData:
    """
    .. seealso:: :class:`.FunctionData`
    """

    #: If True, don't wrap this
    ignore: bool = False

    #: If True, don't wrap this, but provide a pure virtual implementation
    ignore_pure: bool = False

    #: Most of the time, you will want to specify ``ignore`` instead.
    #:
    #: If True, don't expose this function to python. If a trampoline is supposed
    #: to be generated, it will still be generated. You will likely want to use
    #: ``trampoline_cpp_code`` if you specify this.
    ignore_py: bool = False

    #: Generate this in an `#ifdef`
    ifdef: Optional[str] = None
    #: Generate this in an `#ifndef`
    ifndef: Optional[str] = None

    #: Use this code instead of the generated code
    cpp_code: Optional[str] = None

    #: Docstring for the function, will attempt to convert Doxygen docs if omitted
    doc: Optional[str] = None

    #: Text to append to the (autoconverted) docstring for the function
    doc_append: Optional[str] = None

    #: Disallow implicit conversions from None for all parameters. See also
    #: ``disable_none`` in ParamData.
    disable_none: Optional[bool] = None

    #: If True, prepends an underscore to the python name
    internal: bool = False

    #: Use this to set the name of the function as exposed to python
    #:
    #: When applied to a constructor, creates a static method for the overload instead.
    rename: Optional[str] = None

    #: Mechanism to override individual parameters. For example, to rename the first
    #: parameter of ``void my_function(int param1)``:
    #:
    #: .. code-block:: yaml
    #:
    #:    functions:
    #:        my_function:
    #:            param_override:
    #:                 param1:
    #:
    param_override: Dict[str, ParamData] = dataclasses.field(default_factory=dict)

    #: If specified, put the function in a sub.pack.age
    subpackage: Optional[str] = None

    #: By default, semiwrap will release the GIL whenever a wrapped
    #: function is called.
    no_release_gil: Optional[bool] = None

    #: Configures parameters that can receive objects that implement the buffer protocol
    buffers: List[BufferData] = dataclasses.field(default_factory=list)

    #: Adds py::keep_alive<x,y> to the function. Overrides automatic
    #: keepalive support, which retains references passed to constructors.
    #: https://pybind11.readthedocs.io/en/stable/advanced/functions.html#keep-alive
    keepalive: Optional[List[Tuple[int, int]]] = None

    #: https://pybind11.readthedocs.io/en/stable/advanced/functions.html#return-value-policies
    return_value_policy: ReturnValuePolicy = ReturnValuePolicy.automatic

    #: If this is a function template, this is a list of instantiations
    #: that you wish to provide. This is a list of lists, where the inner
    #: list is the template parameters for that function
    template_impls: Optional[List[List[str]]] = None

    #: Specify custom C++ code for the virtual function trampoline
    trampoline_cpp_code: Optional[str] = None

    #: Specify a transformation lambda to be used when this virtual function
    #: is called from C++. This inline code should be a lambda that has the same
    #: arguments as the original C++ virtual function, except the first argument
    #: will be a py::function with the python overload
    #:
    #: cpp_code should also be specified for this to be useful
    #:
    #: For example, to transform a function that takes an iostream into a function
    #: that returns a string:
    #:
    #: .. code-block:: yaml
    #:
    #:    cpp_code: |
    #:      [](MyClass* self) {
    #:        return "string";
    #:      }
    #:    virtual_xform: |
    #:      [](py::function fn, MyClass* self, std::iostream &is) {
    #:         std::string d = py::cast(fn());
    #:         is << d;
    #:      }
    #:
    virtual_xform: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class FunctionData(OverloadData):
    """
    Customize the way the autogenerator binds a function.

    .. code-block:: yaml

       functions:
         # for non-overloaded functions, just specify the name + customizations
         name_of_non_overloaded_fn:
           # add customizations for function here

         # For overloaded functions, specify the name, but each overload
         # separately
         my_overloaded_fn:
           overloads:
             int, int:
               # customizations for `my_overloaded_fn(int, int)`
             int, int, int:
               # customizations for `my_overloaded_fn(int, int, int)`
    """

    #: See above
    overloads: Dict[str, OverloadData] = dataclasses.field(default_factory=dict)


class PropAccess(enum.Enum):
    """Whether a property is writable."""

    #: Determine read/read-write automatically:
    #:
    #: * If a struct/union, default to readwrite
    #: * If a class, default to readwrite if a basic type that isn't a
    #:   reference, otherwise default to readonly
    auto = "auto"

    #: Allow python users access to the value, but ensure it can't
    #: change. This is useful for properties that are defined directly
    #: in the class
    readonly = "readonly"

    #: Allows python users to read/write the value
    readwrite = "readwrite"


@dataclasses.dataclass(frozen=True)
class PropData:
    #: If set to True, this property is not made available to python
    ignore: bool = False

    #: Set the python name of this property to the specified string
    rename: Optional[str] = None

    #: Python code access to this property
    access: PropAccess = PropAccess.auto

    #: Docstring for the property (only available on class properties)
    doc: Optional[str] = None

    #: Text to append to the (autoconverted) docstring
    doc_append: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class EnumValue:
    #: If set to True, this property is not made available to python
    ignore: bool = False

    #: Set the python name of this enum value to the specified string
    rename: Optional[str] = None

    #: Docstring for the enum value
    doc: Optional[str] = None

    #: Text to append to the (autoconverted) docstring
    doc_append: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class EnumData:
    #: Set your own docstring for the enum
    doc: Optional[str] = None

    #: Text to append to the (autoconverted) docstring
    doc_append: Optional[str] = None

    #: If set to True, this property is not made available to python
    ignore: bool = False

    #: Set the python name of this enum to the specified string
    rename: Optional[str] = None

    #: Remove this prefix from autogenerated enum value name
    value_prefix: Optional[str] = None

    #: If specified, put the enum in a sub.pack.age (ignored for
    #: enums that are part of classes)
    subpackage: Optional[str] = None

    #: Enum value configuration
    values: Dict[str, EnumValue] = dataclasses.field(default_factory=dict)

    #: This will insert code right before the semicolon ending the enum py
    #: definition. You can use this to easily insert additional custom values
    #: without using the global inline_code mechanism.
    inline_code: Optional[str] = None

    #: Tell pybind11 to create an enumeration that also supports rudimentary
    #: arithmetic and bit-level operations like comparisons, and, or, xor,
    #: negation, etc.
    arithmetic: bool = False


@dataclasses.dataclass(frozen=True)
class ClassData:
    #: Docstring for the class
    doc: Optional[str] = None

    #: Text to append to the (autoconverted) docstring
    doc_append: Optional[str] = None

    #: Ignore this class
    ignore: bool = False

    #: List of bases to ignore. Name must include any template specializations.
    ignored_bases: List[str] = dataclasses.field(default_factory=list)

    #: Specify fully qualified names for the bases. If the base has a template
    #: parameter, you must include it. Only needed if it can't be automatically
    #: detected directly from the text.
    base_qualnames: Dict[str, str] = dataclasses.field(default_factory=dict)

    #: Customize attributes of the class
    #:
    #: .. code-block:: yaml
    #:
    #:    classes:
    #:      MyClass:
    #:        attributes:
    #:          m_attr:
    attributes: Dict[str, PropData] = dataclasses.field(default_factory=dict)

    #: Customize enums
    #:
    #: .. code-block:: yaml
    #:
    #:    classes:
    #:      MyClass:
    #:        enums:
    #:          MyEnum:
    enums: Dict[str, EnumData] = dataclasses.field(default_factory=dict)

    #: Customize methods
    #:
    #: .. code-block:: yaml
    #:
    #:    classes:
    #:      MyClass:
    #:        methods:
    #:          mymethod:
    methods: Dict[str, FunctionData] = dataclasses.field(default_factory=dict)

    #: Inform the autogenerator that this class is polymorphic
    is_polymorphic: Optional[bool] = None

    #: Disable generating a trampoline for this class
    force_no_trampoline: bool = False

    #: Disable generating a default constructor for this class
    force_no_default_constructor: bool = False

    #: pybind11 will detect multiple inheritance automatically if a
    #: class directly derives from multiple classes. However,
    #: If the class derives from classes that participate in multiple
    #: inheritance, pybind11 won't detect it automatically, so this
    #: flag is needed.
    force_multiple_inheritance: bool = False

    #: If there are circular dependencies, this will help you resolve them
    #: manually. TODO: make it so we don't need this
    force_depends: List[str] = dataclasses.field(default_factory=list)

    #: Use this to bring in type casters for a particular type that may have
    #: been hidden (for example, with a typedef or definition in another file),
    #: instead of explicitly including the header. This should be the full
    #: namespace of the type.
    force_type_casters: List[str] = dataclasses.field(default_factory=list)

    #: If the object shouldn't be deleted by pybind11, use this. Disables
    #: implicit constructors.
    nodelete: bool = False

    #: Set the python name of the class to this
    rename: Optional[str] = None

    #: If specified, put the class in a sub.pack.age. Ignored
    #: for functions attached to a class. When template parameters
    #: are used, must define subpackage on template instances
    #: instead
    subpackage: Optional[str] = None

    #: Extra 'using' directives to insert into the trampoline and the
    #: wrapping scope
    typealias: List[str] = dataclasses.field(default_factory=list)

    #: Fully-qualified pre-existing constant that will be inserted into the
    #: trampoline and wrapping scopes as a constexpr
    constants: List[str] = dataclasses.field(default_factory=list)

    #: If this is a template class, a list of the parameters if it can't
    #: be autodetected (currently can't autodetect). If there is no space
    #: in the parameter, then it is assumed to be a 'typename', otherwise
    #: the parameter is split by space and the first item is the type and
    #: the second parameter is the name (useful for integral templates)
    template_params: Optional[List[str]] = None

    #: If this is a template class, the specified C++ code is inserted
    #: into the template definition
    template_inline_code: str = ""

    #: If this class has an associated trampoline, add this code inline at
    #: the bottom of the trampoline class. This is rarely useful.
    trampoline_inline_code: Optional[str] = None

    #: This will insert code right before the semicolon ending the class py
    #: definition. You can use this to easily insert additional custom functions
    #: without using the global inline_code mechanism.
    #:
    #: .. code-block: C++
    #:
    #:   cls_MyClass
    #:      .def("something", &MyClass::Something)  // autogenerated
    #:      // inline code is inserted here
    #:      ;
    #:
    inline_code: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class TemplateData:
    """
    Instantiates a template as a python type. To customize the class,
    add it to the ``classes`` key and specify the template type.

    Code to be wrapped:

    .. code-block:: c++

        template <typename T>
        class MyClass {};

    To bind ``MyClass<int>`` as the python class ``MyIntClass``, add this
    to your YAML:

    .. code-block:: yaml

        classes:
          MyClass:
            template_params:
            - T

        templates:
          MyIntClass:
            qualname: MyClass
            params:
            - int
    """

    #: Fully qualified name of instantiated class
    qualname: str

    #: Template parameters to use
    params: List[Union[str, int]]

    #: If specified, put the template instantiation in a sub.pack.age
    subpackage: Optional[str] = None

    #: Set the docstring for the template instance
    doc: Optional[str] = None

    #: Text to append to the (autoconverted) docstring for the template instance
    doc_append: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Defaults:
    """
    Defaults to apply to everything

    .. code-block:: yaml

        defaults:
          ignore: true
          report_ignored_missing: false

    """

    #: Set this to True to ignore functions/enums/classes at namespace scope
    #: by default if they aren't present in the YAML
    ignore: bool = False

    #: If False and default ignore is True, don't report missing items
    report_ignored_missing: bool = True


@dataclasses.dataclass(frozen=True)
class AutowrapConfigYaml:
    """
    Format of the files specified by ``[tool.semiwrap.extension_modules."PACKAGENAME".headers]``.
    Each key in this data structure is a toplevel key in the YAML file.
    """

    #: Provides a mechanism to specify certain default behaviors
    defaults: Defaults = dataclasses.field(default_factory=Defaults)

    #: When specified,
    #:
    #: .. code-block:: yaml
    #:
    #:    strip_prefixes:
    #:    - FOO_  # any functions that begin with FOO_ will have it stripped
    strip_prefixes: List[str] = dataclasses.field(default_factory=list)

    #: Adds ``#include <FILENAME>`` directives to the top of the autogenerated
    #: C++ file, after autodetected include dependencies are inserted.
    #:
    #: .. code-block:: yaml
    #:
    #:    extra_includes:
    #:    - foo.h
    extra_includes: List[str] = dataclasses.field(default_factory=list)

    #: Adds ``#include <FILENAME>`` directives after semiwrap.h is
    #: included, but before any autodetected include dependencies. Only use
    #: this when dealing with broken headers.
    #:
    #: .. code-block:: yaml
    #:
    #:    extra_includes_first:
    #:    - foo.h
    extra_includes_first: List[str] = dataclasses.field(default_factory=list)

    #: Specify raw C++ code that will be inserted at the end of the
    #: autogenerated file, inside a function. This is useful for extending
    #: your classes or providing other customizations. The following C++
    #: variables are available:
    #:
    #: * ``m`` is the ``py::module`` instance
    #: * ``cls_CLASSNAME`` are ``py::class`` instances
    #: * ... lots of other things too
    #:
    #: The trampoline class (useful for accessing protected items) is available
    #: at ``{CLASSNAME}_Trampoline``
    #:
    #: To see the full list, run a build and look at the generated code at
    #: ``build/*/gensrc/**/*.cpp``
    #:
    #: Recommend that you use the YAML multiline syntax to specify it:
    #:
    #: .. code-block:: yaml
    #:
    #:    inline_code: |
    #:      cls_CLASSNAME.def("get42", []() { return 42; });
    inline_code: Optional[str] = None

    #: Key is the attribute (variable) name
    #:
    #: .. code-block:: yaml
    #:
    #:    attributes:
    #:      my_variable:
    #:        # customizations here, see PropData
    #:
    attributes: Dict[str, PropData] = dataclasses.field(default_factory=dict)

    #: Key is the namespace + class name
    #:
    #: .. code-block:: yaml
    #:
    #:    classes:
    #:      NAMESPACE::CLASSNAME:
    #:        # customizations here, see ClassData
    #:
    classes: Dict[str, ClassData] = dataclasses.field(default_factory=dict)

    #: Key is the function name
    #:
    #: .. code-block:: yaml
    #:
    #:    functions:
    #:      fn_name:
    #:        # customizations here, see FunctionData
    #:
    functions: Dict[str, FunctionData] = dataclasses.field(default_factory=dict)

    #: Key is the enum name, for enums at global scope
    #:
    #: .. code-block:: yaml
    #:
    #:    enums:
    #:      MyEnum:
    #:        # customizations here, see EnumData
    #:
    enums: Dict[str, EnumData] = dataclasses.field(default_factory=dict)

    #: Instantiates a template. Key is the name to give to the Python type.
    #:
    #: .. code-block:: yaml
    #:
    #:    templates:
    #:      ClassName:
    #:        # customizations here, see TemplateData
    #:
    templates: Dict[str, TemplateData] = dataclasses.field(default_factory=dict)

    #: Extra 'using' directives to insert into the trampoline and the
    #: wrapping scope
    #:
    #: .. code-block:: yaml
    #:
    #:    typealias:
    #:    # makes SomeClass available in the wrapping scope
    #:    - some_namespace::SomeClass
    #:
    typealias: List[str] = dataclasses.field(default_factory=list)

    #: Encoding to use when opening this header file
    encoding: str = "utf-8-sig"

    @classmethod
    def from_file(cls, fname) -> "AutowrapConfigYaml":
        with open(fname) as fp:
            data = yaml.safe_load(fp)

        if data is None:
            data = {}

        data = fix_yaml_dict(data)

        return parse_input(data, cls, fname)
