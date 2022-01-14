#
# Defines data that is consumed by the header2whatever hooks/templates
# to modify the generated files
#

import enum
from typing import Dict, List, Tuple, Optional

from pydantic import validator
from .util import Model, _generating_documentation


class ParamData(Model):
    """Various ways to modify parameters"""

    #: Set parameter name to this
    name: Optional[str] = None

    #: Change C++ type emitted
    x_type: Optional[str] = None

    #: Default value for parameter
    default: Optional[str] = None

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


class BufferData(Model):

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

    TAKE_OWNERSHIP = "take_ownership"
    COPY = "copy"
    MOVE = "move"
    REFERENCE = "reference"
    REFERENCE_INTERNAL = "reference_internal"
    AUTOMATIC = "automatic"
    AUTOMATIC_REFERENCE = "automatic_reference"


class FunctionData(Model):
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

    #: If True, don't wrap this
    ignore: bool = False

    #: If True, don't wrap this, but provide a pure virtual implementation
    ignore_pure: bool = False

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

    #: If True, prepends an underscore to the python name
    internal: bool = False

    #: Use this to set the name of the function as exposed to python
    rename: Optional[str] = None

    #: Mechanism to override individual parameters
    param_override: Dict[str, ParamData] = {}

    #: If specified, put the function in a sub.pack.age
    subpackage: Optional[str] = None

    #: By default, robotpy-build will release the GIL whenever a wrapped
    #: function is called.
    no_release_gil: Optional[bool] = None

    buffers: List[BufferData] = []

    overloads: Dict[str, "FunctionData"] = {}

    #: Adds py::keep_alive<x,y> to the function. Overrides automatic
    #: keepalive support, which retains references passed to constructors.
    #: https://pybind11.readthedocs.io/en/stable/advanced/functions.html#keep-alive
    keepalive: Optional[List[Tuple[int, int]]] = None

    #: https://pybind11.readthedocs.io/en/stable/advanced/functions.html#return-value-policies
    return_value_policy: ReturnValuePolicy = ReturnValuePolicy.AUTOMATIC

    #: If this is a function template, this is a list of instantiations
    #: that you wish to provide. This is a list of lists, where the inner
    #: list is the template parameters for that function
    template_impls: Optional[List[List[str]]] = None

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

    @validator("overloads", pre=True)
    def validate_overloads(cls, value):
        for k, v in value.items():
            if v is None:
                value[k] = FunctionData()
        return value


if not _generating_documentation:
    FunctionData.update_forward_refs()


class PropAccess(enum.Enum):

    #: Determine read/read-write automatically:
    #:
    #: * If a struct/union, default to readwrite
    #: * If a class, default to readwrite if a basic type that isn't a
    #:   reference, otherwise default to readonly
    AUTOMATIC = "auto"

    #: Allow python users access to the value, but ensure it can't
    #: change. This is useful for properties that are defined directly
    #: in the class
    READONLY = "readonly"

    #: Allows python users to read/write the value
    READWRITE = "readwrite"


class PropData(Model):

    #: If set to True, this property is not made available to python
    ignore: bool = False

    #: Set the python name of this property to the specified string
    rename: Optional[str]

    #: Python code access to this property
    access: PropAccess = PropAccess.AUTOMATIC

    #: Docstring for the property (only available on class properties)
    doc: Optional[str] = None

    #: Text to append to the (autoconverted) docstring
    doc_append: Optional[str] = None


class EnumValue(Model):

    #: If set to True, this property is not made available to python
    ignore: bool = False

    #: Set the python name of this enum value to the specified string
    rename: Optional[str] = None

    #: Docstring for the enum value
    doc: Optional[str] = None

    #: Text to append to the (autoconverted) docstring
    doc_append: Optional[str] = None


class EnumData(Model):

    #: Set your own docstring for the enum
    doc: Optional[str] = None

    #: Text to append to the (autoconverted) docstring
    doc_append: Optional[str] = None

    #: If set to True, this property is not made available to python
    ignore: bool = False

    #: Set the python name of this enum to the specified string
    rename: Optional[str] = None

    value_prefix: Optional[str] = None

    #: If specified, put the enum in a sub.pack.age (ignored for
    #: enums that are part of classes)
    subpackage: Optional[str] = None

    values: Dict[str, EnumValue] = {}


class ClassData(Model):

    #: Docstring for the class
    doc: Optional[str] = None

    #: Text to append to the (autoconverted) docstring
    doc_append: Optional[str] = None

    ignore: bool = False
    ignored_bases: List[str] = []

    #: Specify fully qualified names for the bases
    base_qualnames: Dict[str, str] = {}

    attributes: Dict[str, PropData] = {}
    enums: Dict[str, EnumData] = {}
    methods: Dict[str, FunctionData] = {}

    is_polymorphic: bool = False
    force_no_trampoline: bool = False
    force_no_default_constructor: bool = False

    #: If there are circular dependencies, this will help you resolve them
    #: manually. TODO: make it so we don't need this
    force_depends: List[str] = []

    #: Use this to bring in type casters for a particular type that may have
    #: been hidden (for example, with a typedef or definition in another file),
    #: instead of explicitly including the header. This should be the full
    #: namespace of the type.
    force_type_casters: List[str] = []

    #: If the object shouldn't be deleted by pybind11, use this. Disables
    #: implicit constructors.
    nodelete: bool = False

    #: Set the python name of the class to this
    rename: Optional[str] = None

    #: This is deprecated and has no effect
    shared_ptr: bool = True

    #: If specified, put the class in a sub.pack.age. Ignored
    #: for functions attached to a class. When template parameters
    #: are used, must define subpackage on template instances
    #: instead
    subpackage: Optional[str] = None

    #: Extra 'using' directives to insert into the trampoline and the
    #: wrapping scope
    typealias: List[str] = []

    #: Extra constexpr to insert into the trampoline and wrapping scopes
    constants: List[str] = []

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

    @validator("attributes", pre=True)
    def validate_attributes(cls, value):
        for k, v in value.items():
            if v is None:
                value[k] = PropData()
        return value

    @validator("enums", pre=True)
    def validate_enums(cls, value):
        for k, v in value.items():
            if v is None:
                value[k] = EnumData()
        return value

    @validator("methods", pre=True)
    def validate_methods(cls, value):
        for k, v in value.items():
            if v is None:
                value[k] = FunctionData()
        return value


class TemplateData(Model):
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
    params: List[str]

    #: If specified, put the template instantiation in a sub.pack.age
    subpackage: Optional[str] = None

    #: Set the docstring for the template instance
    doc: Optional[str] = None

    #: Text to append to the (autoconverted) docstring for the template instance
    doc_append: Optional[str] = None


class HooksDataYaml(Model):
    """
    Format of the file in [tool.robotpy-build.wrappers."PACKAGENAME"]
    generation_data
    """

    strip_prefixes: List[str] = []

    #: Adds ``#include <FILENAME>`` directives to the top of the autogenerated
    #: C++ file, after autodetected include dependencies are inserted.
    extra_includes: List[str] = []

    #: Adds ``#include <FILENAME>`` directives after robotpy_build.h is
    #: included, but before any autodetected include dependencies. Only use
    #: this when dealing with broken headers.
    extra_includes_first: List[str] = []

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
    attributes: Dict[str, PropData] = {}

    #: Key is the class name
    #:
    #: .. code-block:: yaml
    #:
    #:    classes:
    #:      CLASSNAME:
    #:        # customizations here, see ClassData
    #:
    classes: Dict[str, ClassData] = {}

    #: Key is the function name
    #:
    #: .. code-block:: yaml
    #:
    #:    functions:
    #:      fn_name:
    #:        # customizations here, see FunctionData
    #:
    functions: Dict[str, FunctionData] = {}

    #: Key is the enum name, for enums at global scope
    #:
    #: .. code-block:: yaml
    #:
    #:    enums:
    #:      MyEnum:
    #:        # customizations here, see EnumData
    #:
    enums: Dict[str, EnumData] = {}

    #: Instantiates a template. Key is the name to give to the Python type.
    #:
    #: .. code-block:: yaml
    #:
    #:    templates:
    #:      ClassName:
    #:        # customizations here, see TemplateData
    #:
    templates: Dict[str, TemplateData] = {}

    @validator("attributes", pre=True)
    def validate_attributes(cls, value):
        for k, v in value.items():
            if v is None:
                value[k] = PropData()
        return value

    @validator("classes", pre=True)
    def validate_classes(cls, value):
        for k, v in value.items():
            if v is None:
                value[k] = ClassData()
        return value

    @validator("enums", pre=True)
    def validate_enums(cls, value):
        for k, v in value.items():
            if v is None:
                value[k] = EnumData()
        return value

    @validator("functions", pre=True)
    def validate_functions(cls, value):
        for k, v in value.items():
            if v is None:
                value[k] = FunctionData()
        return value
