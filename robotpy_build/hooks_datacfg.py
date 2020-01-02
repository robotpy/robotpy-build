#
# Defines data that is consumed by the header2whatever hooks/templates
# to modify the generated files
#

import enum
from typing import Dict, List, Optional

from pydantic import BaseModel, validator


class Model(BaseModel):
    class Config:
        extra = "forbid"


class ParamData(Model):
    """Various ways to modify parameters"""

    # C++ type emitted
    x_type: Optional[str] = None

    # Default value for parameter
    default: Optional[str] = None


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


class FunctionData(Model):
    # If True, don't wrap this
    ignore: bool = False

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

    no_release_gil: bool = False

    buffers: List[BufferData] = []

    overloads: Dict[str, "FunctionData"] = {}

    @validator("overloads", pre=True)
    def validate_overloads(cls, value):
        for k, v in value.items():
            if v is None:
                value[k] = FunctionData()
        return value


FunctionData.update_forward_refs()


class PropData(Model):
    ignore: bool = False

    #: Set the name of this property to the specified value
    rename: Optional[str]

    #: Allow python users access to the value, but ensure it can't
    #: change. This is useful for properties that are defined directly
    #: in the class, as opposed to being a reference or pointer.
    readonly: bool = False


class EnumData(Model):
    ignore: bool = False
    value_prefix: Optional[str] = None


class ClassData(Model):

    ignore: bool = False
    ignored_bases: List[str] = []

    attributes: Dict[str, PropData] = {}
    enums: Dict[str, EnumData] = {}
    methods: Dict[str, FunctionData] = {}

    is_polymorphic: bool = False

    #: If the type was created as a shared_ptr (such as via std::make_shared)
    #: then pybind11 needs to be informed of this.
    #:
    #: https://github.com/pybind/pybind11/issues/1215
    #:
    #: One way you can tell we messed this up is if there's a double-free
    #: error and the stack trace involves a unique_ptr destructor
    shared_ptr: bool = True

    #: Extra 'using' directives to insert into the trampoline and the
    #: wrapping scope
    typealias: List[str] = []

    #: Extra constexpr to insert into the trampoline and wrapping scopes
    constants: List[str] = []

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


class HooksDataYaml(Model):
    """
        Format of the file in [tool.robotpy-build.wrappers."PACKAGENAME"]
        generation_data
    """

    strip_prefixes: List[str] = []
    extra_includes: List[str] = []

    attributes: Dict[str, PropData] = {}
    classes: Dict[str, ClassData] = {}
    functions: Dict[str, FunctionData] = {}
    enums: Dict[str, EnumData] = {}

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
