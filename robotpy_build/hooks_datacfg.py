#
# Defines data that is consumed by the header2whatever hooks/templates
# to modify the generated files
#

import enum
from typing import Dict, List, Tuple, Optional

from pydantic import BaseModel, validator


class Model(BaseModel):
    class Config:
        extra = "forbid"


class ParamData(Model):
    """Various ways to modify parameters"""

    # Rename parameter
    name: Optional[str] = None

    # C++ type emitted
    x_type: Optional[str] = None

    # Default value for parameter
    default: Optional[str] = None

    force_out: bool = False

    ignore: bool = False


class BufferType(str, enum.Enum):
    IN = "in"
    OUT = "out"
    INOUT = "inout"


class BufferData(Model):
    """Describes buffers"""

    # Indicates what type of buffer is required: out/inout buffers require
    # a writeable buffer such as a bytearray, but in only needs a readonly
    # buffer (such as bytes)
    type: BufferType

    # Name of source parameter -- user must pass in something that implements
    # the buffer protocol (eg bytes, bytearray)
    src: str

    # Name of length parameter. An out-only parameter, it will be set to the size
    # of the src buffer, and will be returned so the caller can determine how
    # many bytes were written
    len: str

    # If specified, the minimum size of the passed in buffer
    minsz: Optional[int] = None


class ReturnValuePolicy(enum.Enum):
    """
        see pybind11 documentation for this
    """

    TAKE_OWNERSHIP = "take_ownership"
    COPY = "copy"
    MOVE = "move"
    REFERENCE = "reference"
    REFERENCE_INTERNAL = "reference_internal"
    AUTOMATIC = "automatic"
    AUTOMATIC_REFERENCE = "automatic_reference"


class FunctionData(Model):
    # If True, don't wrap this
    ignore: bool = False

    # If True, don't wrap this, but provide a pure virtual implementation
    # -> in theory we could autodetect this, but sometimes ignore
    #    is used for when CppHeaderParser totally blows it
    ignore_pure: bool = False

    # Generate this in an `#ifdef`
    ifdef: Optional[str] = None
    # Generate this in an `#ifndef`
    ifndef: Optional[str] = None

    # Use this code instead of the generated code
    cpp_code: Optional[str] = None

    # Docstring for the function
    doc: Optional[str] = None

    # If True, prepends an underscore to the python name
    internal: bool = False

    # Set this to rename the function
    rename: Optional[str] = None

    # Mechanism to override individual parameters
    param_override: Dict[str, ParamData] = {}

    #: If specified, put the function in a sub.pack.age
    subpackage: Optional[str] = None

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

    @validator("overloads", pre=True)
    def validate_overloads(cls, value):
        for k, v in value.items():
            if v is None:
                value[k] = FunctionData()
        return value


FunctionData.update_forward_refs()


class PropAccess(enum.Enum):

    #: Determine read/read-write automatically:
    #: - If a struct/union, default to readwrite
    #: - If a class, default to readwrite if a basic type that isn't a
    #:   reference, otherwise default to readonly
    AUTOMATIC = "auto"

    #: Allow python users access to the value, but ensure it can't
    #: change. This is useful for properties that are defined directly
    #: in the class
    READONLY = "readonly"

    #: Allows python users to read/write the value
    READWRITE = "readwrite"


class PropData(Model):
    ignore: bool = False

    #: Set the name of this property to the specified value
    rename: Optional[str]

    #: Python code access to this property
    access: PropAccess = PropAccess.AUTOMATIC

    #: Docstring for the property (only available on class properties)
    doc: Optional[str] = None


class EnumValue(Model):
    ignore: bool = False
    rename: Optional[str] = None

    #: Docstring for the enum value
    doc: Optional[str] = None


class EnumData(Model):

    # Docstring for the enum
    doc: Optional[str] = None

    ignore: bool = False
    rename: Optional[str] = None
    value_prefix: Optional[str] = None

    #: If specified, put the enum in a sub.pack.age (ignored for
    #: enums that are part of classes)
    subpackage: Optional[str] = None

    values: Dict[str, EnumValue] = {}


class ClassData(Model):

    #: Docstring for the class
    doc: Optional[str] = None

    ignore: bool = False
    ignored_bases: List[str] = []

    # Specify fully qualified names for the bases
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

    #: If the object shouldn't be deleted by pybind11, use this. Disables
    #: implicit constructors.
    nodelete: bool = False

    #: Set the python name of the class to this
    rename: Optional[str] = None

    #: If the type was created as a shared_ptr (such as via std::make_shared)
    #: then pybind11 needs to be informed of this.
    #:
    #: https://github.com/pybind/pybind11/issues/1215
    #:
    #: One way you can tell we messed this up is if there's a double-free
    #: error and the stack trace involves a unique_ptr destructor
    shared_ptr: bool = True

    #: If specified, put the class in a sub.pack.age. Ignored
    #: for functions attached to a class.
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

    # Fully qualified name of template
    qualname: str

    # Template parameters to use
    params: List[str]

    # TODO: other parameters useful for concrete types


class HooksDataYaml(Model):
    """
        Format of the file in [tool.robotpy-build.wrappers."PACKAGENAME"]
        generation_data
    """

    strip_prefixes: List[str] = []
    extra_includes: List[str] = []
    # sticks these includes first, for really broken headers
    extra_includes_first: List[str] = []
    inline_code: Optional[str] = None

    attributes: Dict[str, PropData] = {}
    classes: Dict[str, ClassData] = {}
    functions: Dict[str, FunctionData] = {}
    enums: Dict[str, EnumData] = {}

    #: Instantiates a template. Key is the name to give to the Python type
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
