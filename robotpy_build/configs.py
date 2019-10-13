# For validating pyproject.toml

from schematics.models import Model
from schematics.types import ModelType, BooleanType, StringType, ListType, DictType


class WrapperConfig(Model):
    """
        Wrapper configurations specified in pyproject.toml

        [tool.robotpy-build.wrappers."package-name"]
    """

    # List of extra headers to export
    extra_headers = ListType(StringType, default=[])

    # List of robotpy-build library dependencies
    # .. would be nice to auto-infer this from the python install dependencies
    depends = ListType(StringType, default=[])

    #
    # Download settings
    #

    # Library name
    libname = StringType(required=True)

    # Name of artifact to download, if different than libname
    artname = StringType(default="")

    # URL to download
    baseurl = StringType(required=True)

    # Version of artifact to download
    version = StringType(required=True)

    #
    # Wrapper generation settings
    #

    # Source files to compile
    sources = ListType(StringType, default=[])

    # List of dictionaries: each dictionary key is the function
    # name for the initialization function, the value is the
    # header that is being wrapped
    generate = ListType(DictType(StringType))

    # Path to a data.yml to use during code generation
    generation_data = StringType()


class DistutilsMetadata(Model):

    name = StringType(required=True)
    description = StringType()

    author = StringType(required=True)
    author_email = StringType()
    url = StringType()
    license = StringType(required=True)
    install_requires = ListType(StringType, required=True)

    # robotpy-build sets these automatically
    # long_description
    # zip_safe
    # include_package_data
    # requires_python
    # packages
    # version
    # cmdclass
    # ext_modules


class RobotpyBuildConfig(Model):
    """
        Main robotpy-build configuration specified in pyproject.toml

        [tool.robotpy-build]
    """

    # package to store version information in
    base_package = StringType(required=True)

    #
    # Everything below here are separate sections
    #

    # [tool.robotpy-build.metadata]
    metadata = ModelType(DistutilsMetadata)

    # [tool.robotpy-build.wrappers."XXX"]
    wrappers = DictType(ModelType(WrapperConfig))
