#
# Defines data that is consumed by the header2whatever hooks/templates
# to modify the generated files
#

import enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class ParamData(BaseModel):
    """Various ways to modify parameters"""

    # C++ type emitted
    x_type: Optional[str] = None

    # Default value for parameter
    default: Optional[str] = None


class BufferType(str, enum.Enum):
    IN = "in"
    OUT = "out"
    INOUT = "inout"


class BufferData(BaseModel):
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


class FunctionData(BaseModel):
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


class MethodData(FunctionData):
    overloads: Optional[Dict[str, FunctionData]] = None


class ClassData(BaseModel):
    ignore: bool = False
    methods: Dict[str, MethodData] = {}


class EnumData(BaseModel):
    value_prefix: Optional[str] = None


class HooksDataYaml(BaseModel):
    """
        Format of the file in [tool.robotpy-build.wrappers."PACKAGENAME"]
        generation_data
    """

    strip_prefixes: List[str] = []
    extra_includes: List[str] = []
    functions: Dict[str, FunctionData] = {}
    classes: Dict[str, ClassData] = {}
    enums: Dict[str, EnumData] = {}
