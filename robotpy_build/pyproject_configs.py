# For validating pyproject.toml

from typing import Dict, List, Optional

from pydantic import BaseModel


class MavenLibDownload(BaseModel):
    """
        The information required here can be found in the vendor JSON file
    """

    class Config:
        extra = "forbid"

    #: Maven artifact ID
    artifact_id: str

    #: Maven group ID
    group_id: str

    #: Maven repository URL
    repo_url: str

    #: Version of artifact to download
    version: str

    #: Names of contained shared libraries (in loading order). If None,
    #: set to artifact_id.
    libs: Optional[List[str]] = None

    #: Names of contained shared link only libraries (in loading order). If None,
    #: set to name. If empty list, link only libs will not be downloaded.
    dlopenlibs: Optional[List[str]] = None

    #: Library extensions map
    libexts: Dict[str, str] = {}

    #: Compile time extensions map
    linkexts: Dict[str, str] = {}

    #: When set, download sources instead of downloading libraries. When
    #: using this, you need to manually add the sources to the configuration
    #: to be compiled.
    use_sources: bool = False

    #: If use_sources is set, this is the list of sources to compile
    sources: Optional[List[str]] = None

    #: Configure the sources classifier
    sources_classifier: str = "sources"


class StaticLibConfig(BaseModel):
    class Config:
        extra = "forbid"

    #: If this project depends on external libraries stored in a maven repo
    #: specify it here
    maven_lib_download: MavenLibDownload

    #: If True, skip this library; typically used in conjection with an override
    ignore: bool = False


class WrapperConfig(BaseModel):
    """
        Buildable package configurations specified in pyproject.toml

        [tool.robotpy-build.wrappers."package-name"]
    """

    class Config:
        extra = "forbid"

    #: Name that other projects can use in their dependency list.
    name: str

    #: Name of extension to build. If None, set to _{name}
    extension: Optional[str] = None

    #: Name of generated file that ensures the shared libraries and any
    #: dependencies are loaded. Defaults to _init{extension}.py
    libinit: Optional[str] = None

    # List of robotpy-build library dependencies
    # .. would be nice to auto-infer this from the python install dependencies
    depends: List[str] = []

    #: If this project depends on external libraries stored in a maven repo
    #: specify it here
    maven_lib_download: Optional[MavenLibDownload] = None

    # List of extra include directories to export, relative to the
    # project root
    extra_includes: List[str] = []

    # Source files to compile. Path is relative to the root of
    # the project.
    sources: List[str] = []

    # List of dictionaries: each dictionary key is the function name for
    # the initialization function, the value is the header that is
    # being wrapped. The header is first looked look relative to the
    # package, then relative to each include directory (including
    # downloaded and extracted packages).
    generate: Optional[List[Dict[str, str]]] = None

    # Path to a data.yml to use during code generation, or a directory
    # of yaml files. If a directory, generation data will be looked up
    # using the key in the generate dictionary
    generation_data: Optional[str] = None

    # Specifies type casters that this package exports. robotpy-build
    # will attempt to detect these types at generation time and include
    # them in generated wrappers.
    #
    # [tool.robotpy-build.wrappers."package-name".type_casters]
    # "namespace_type1_type_caster.h" = ["namespace::type1", .. ]
    #
    type_casters: Dict[str, List[str]] = {}

    # Preprocessor definitions
    pp_defines: List[str] = []

    #: If True, skip this wrapper; typically used in conjection with an override
    ignore: bool = False


class DistutilsMetadata(BaseModel):
    class Config:
        # allow passing in extra keywords to setuptools
        extra = "allow"

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
    # python_requires
    # packages
    # version
    # cmdclass
    # ext_modules


class RobotpyBuildConfig(BaseModel):
    """
        Main robotpy-build configuration specified in pyproject.toml

        [tool.robotpy-build]
    """

    class Config:
        extra = "forbid"

    # package to store version information in
    base_package: str

    #
    # Everything below here are separate sections
    #

    # [tool.robotpy-build.metadata]
    metadata: DistutilsMetadata

    # [tool.robotpy-build.wrappers."XXX"]
    wrappers: Dict[str, WrapperConfig] = {}

    # [tool.robotpy-build.static_libs."XXX"]
    static_libs: Dict[str, StaticLibConfig] = {}
