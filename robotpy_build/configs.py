# For validating pyproject.toml

from typing import Dict, List, Optional

from pydantic import BaseModel


class ExtensionConfig(BaseModel):
    """
        Compiled extension specified in pyproject.toml

        [tool.robotpy-build.ext."package-name"]
    """

    # Module name: must match the name given to the PYBIND11_MODULE() macro
    name: str

    # List of robotpy-build library dependencies
    # .. would be nice to auto-infer this from the python install dependencies
    depends: List[str] = []

    # Source files to compile
    sources: List[str]


class WrapperConfig(BaseModel):
    """
        Wrapper configurations specified in pyproject.toml

        [tool.robotpy-build.wrappers."package-name"]
    """

    # List of extra headers to export
    extra_headers: List[str] = []

    # List of robotpy-build library dependencies
    # .. would be nice to auto-infer this from the python install dependencies
    depends: List[str] = []

    #
    # Download settings
    #

    # Project name
    name: str

    # Names of contained shared libraries (in loading order). If None,
    # set to name. If empty list, libs will not be downloaded.
    libs: Optional[List[str]] = None

    # Name of artifact to download, if different than name
    artname: str = ""

    # URL to download
    baseurl: str

    # Version of artifact to download
    version: str

    # Library extensions map
    libexts: Dict[str, str] = {}

    #
    # Wrapper generation settings
    #

    # Source files to compile
    sources: List[str] = []

    # List of dictionaries: each dictionary key is the function
    # name for the initialization function, the value is the
    # header that is being wrapped
    generate: Optional[List[Dict[str, str]]] = None

    # Path to a data.yml to use during code generation
    generation_data: Optional[str] = None


class DistutilsMetadata(BaseModel):

    name: str
    description: Optional[str] = None

    author: str
    author_email: str
    url: str
    license: str
    install_requires: List[str]

    # robotpy-build sets these automatically
    # long_description
    # zip_safe
    # include_package_data
    # requires_python
    # packages
    # version
    # cmdclass
    # ext_modules


class RobotpyBuildConfig(BaseModel):
    """
        Main robotpy-build configuration specified in pyproject.toml

        [tool.robotpy-build]
    """

    # package to store version information in
    base_package: str

    #
    # Everything below here are separate sections
    #

    # [tool.robotpy-build.metadata]
    metadata: DistutilsMetadata

    # [tool.robotpy-build.ext."XXX"]
    ext: Dict[str, ExtensionConfig] = {}

    # [tool.robotpy-build.wrappers."XXX"]
    wrappers: Dict[str, WrapperConfig] = {}
