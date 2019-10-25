#
# Defines data that is consumed by the header2whatever hooks/templates
# to modify the generated files
#

from schematics.models import Model
from schematics.types import (
    ModelType,
    BooleanType,
    IntType,
    StringType,
    ListType,
    DictType,
)


class ParamData(Model):
    """Various ways to modify parameters"""

    class Options:
        serialize_when_none = False

    # C++ type emitted
    x_type = StringType()

    # Default value for parameter
    default = StringType()


class BufferData(Model):
    """Describes buffers"""

    # Indicates what type of buffer is required: out/inout buffers require
    # a writeable buffer such as a bytearray, but in only needs a readonly
    # buffer (such as bytes)
    type = StringType(required=True, choices=["in", "out", "inout"])

    # Name of source parameter -- user must pass in something that implements
    # the buffer protocol (eg bytes, bytearray)
    src = StringType(required=True)

    # Name of length parameter. An out-only parameter, it will be set to the size
    # of the src buffer, and will be returned so the caller can determine how
    # many bytes were written
    len = StringType(required=True)

    # If specified, the minimum size of the passed in buffer
    minsz = IntType()


class FunctionData(Model):
    class Options:
        serialize_when_none = False

    # If True, don't wrap this
    ignore = BooleanType()

    # Use this code instead of the generated code
    cpp_code = StringType()

    # Docstring for the function
    doc = StringType()

    # If True, prepends an underscore to the python name
    internal = BooleanType()

    # Set this to rename the function
    rename = StringType()

    # Mechanism to override individual parameters
    param_override = DictType(ModelType(ParamData), default=lambda: {})

    no_release_gil = BooleanType()

    buffers = ListType(ModelType(BufferData))


class MethodData(FunctionData):
    overloads = DictType(ModelType(FunctionData), default=lambda: {})


class ClassData(Model):
    ignore = BooleanType(default=False)
    methods = DictType(ModelType(MethodData), default=lambda: {})


class EnumData(Model):
    value_prefix = StringType()


class HooksDataYaml(Model):
    """
        Format of the file in [tool.robotpy-build.wrappers."PACKAGENAME"] 
        generation_data
    """

    strip_prefixes = ListType(StringType, default=lambda: [])
    extra_includes = ListType(StringType, default=lambda: [])
    functions = DictType(ModelType(FunctionData), default=lambda: {})
    classes = DictType(ModelType(ClassData), default=lambda: {})
    enums = DictType(ModelType(EnumData), default=lambda: {})
