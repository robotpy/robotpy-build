#
# Defines data that is consumed by the header2whatever hooks/templates
# to modify the generated files
#

from schematics.models import Model
from schematics.types import ModelType, BooleanType, StringType, ListType, DictType


class ParamData(Model):
    """Various ways to modify parameters"""

    class Options:
        serialize_when_none = False

    # C++ type emitted
    x_type = StringType()

    # Default value for parameter
    default = StringType()


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


class MethodData(FunctionData):
    overloads = DictType(ModelType(FunctionData), default=lambda: {})


class ClassData(Model):
    ignore = BooleanType(default=False)
    methods = DictType(ModelType(MethodData), default=lambda: {})
    cpp_inherits = StringType()


class HooksDataYaml(Model):
    """
        Format of the file in [tool.robotpy-build.wrappers."PACKAGENAME"] 
        generation_data
    """

    strip_prefixes = ListType(StringType, default=lambda: [])
    extra_includes = ListType(StringType, default=lambda: [])
    functions = DictType(ModelType(FunctionData), default=lambda: {})
    classes = DictType(ModelType(ClassData), default=lambda: {})
