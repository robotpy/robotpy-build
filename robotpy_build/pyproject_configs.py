#
# pyproject.toml
#

import os
import re
from typing import Dict, List, Optional

from .util import Model

_arch_re = re.compile(r"\{\{\s*ARCH\s*\}\}")
_os_re = re.compile(r"\{\{\s*OS\s*\}\}")


class PatchInfo(Model):
    """
    A unified diff to apply to downloaded source code before building a
    a wrapper.

    .. code-block:: toml

       [[tool.robotpy-build.wrappers."MY.PACKAGE.NAME".maven_lib_download.patches]]
       patch = "path/to/my.patch"
       strip = 0
    """

    #: Name of patch file to apply
    patch: str

    #: Number of directories to strip
    strip: int = 0


class MavenLibDownload(Model):
    """
    Used to download artifacts from a maven repository. This can download
    headers, shared libraries, and sources.

    .. code-block:: toml

       [tool.robotpy-build.wrappers."PACKAGENAME".maven_lib_download]
       artifact_id = "mything"
       group_id = "com.example.thing"
       repo_url = "http://example.com/maven"
       version = "1.2.3"

    .. note:: For FIRST Robotics libraries, the information required can
              be found in the vendor JSON file
    """

    #: Maven artifact ID
    artifact_id: str

    #: Maven group ID
    group_id: str

    #: Maven repository URL
    repo_url: str

    #: Version of artifact to download
    version: str

    #: Configure the sources classifier
    sources_classifier: str = "sources"

    #: When set, download sources instead of downloading libraries. When
    #: using this, you need to manually add the sources to the configuration
    #: to be compiled via :attr:`sources`.
    use_sources: bool = False

    # common with Download

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

    #: If :attr:`use_sources` is set, this is the list of sources to compile
    sources: Optional[List[str]] = None

    #: If :attr:`use_sources` is set, apply the following patches to the sources. Patches
    #: must be in unified diff format.
    patches: Optional[List[PatchInfo]] = None

    #: Patches to downloaded header files. Patches must be in unified diff format.
    header_patches: Optional[List[PatchInfo]] = None


class Download(Model):
    """
    Download sources/libs/includes from a single file

    .. code-block:: toml

       [[tool.robotpy-build.wrappers."PACKAGENAME".download]]
       url = "https://my/url/something.zip"
       incdir = "include"
       libs = ["mylib"]

    """

    #: URL of zipfile to download
    #:
    #: {{ARCH}} and {{OS}} are replaced with the architecture/os name
    url: str

    #: Directory that contains include files.
    #:
    #: {{ARCH}} and {{OS}} are replaced with the architecture/os name
    incdir: Optional[str] = None

    #: Directory that contains library files
    #:
    #: {{ARCH}} and {{OS}} are replaced with the architecture/os name
    libdir: str = ""

    #: Extra include paths, relative to the include directory
    #:
    #: {{ARCH}} and {{OS}} are replaced with the architecture/os name
    extra_includes: List[str] = []

    # Common with MavenLibDownload

    #: If specified, names of contained shared libraries (in loading order)
    libs: Optional[List[str]] = None

    #: If specified, names of contained shared link only libraries (in loading order).
    #: If None, set to name. If empty list, link only libs will not be downloaded.
    dlopenlibs: Optional[List[str]] = None

    #: Library extensions map
    libexts: Dict[str, str] = {}

    #: Compile time extensions map
    linkexts: Dict[str, str] = {}

    #: List of sources to compile
    sources: Optional[List[str]] = None

    #: If :attr:`sources` is set, apply the following patches to the sources. Patches
    #: must be in unified diff format.
    patches: Optional[List[PatchInfo]] = None

    #: Patches to downloaded header files in incdir. Patches must be in unified
    #: diff format.
    header_patches: Optional[List[PatchInfo]] = None

    def _update_with_platform(self, platform):
        for n in ("url", "incdir", "libdir"):
            v = getattr(self, n, None)
            if v is not None:
                v = _os_re.sub(platform.os, _arch_re.sub(platform.arch, v))
                setattr(self, n, v)

        if self.extra_includes:
            self.extra_includes = [
                _os_re.sub(platform.os, _arch_re.sub(platform.arch, v))
                for v in self.extra_includes
            ]


class StaticLibConfig(Model):
    """
    Static libraries that can be consumed as a dependency by other wrappers
    in the same project. Static libraries are not directly installed, and
    as a result cannot be consumed by other projects.

    .. code-block:: toml

       [tool.robotpy-build.static_libs."MY.PACKAGE.NAME"]

    """

    #: If this project depends on external libraries stored in a maven repo
    #: specify it here
    maven_lib_download: Optional[MavenLibDownload] = None

    #: If this project depends on external libraries downloadable from some URL
    #: specify it here
    download: Optional[List[Download]] = None

    #: If True, skip this library; typically used in conjection with an override
    ignore: bool = False


class TypeCasterConfig(Model):
    """
    Specifies type casters that this package exports. robotpy-build
    will attempt to detect these types at generation time and include
    them in generated wrappers.

    .. code-block:: toml

       [[tool.robotpy-build.wrappers."PACKAGENAME".type_casters]]
       header = "my_type_caster.h"
       types = ["foo_t", "ns::ins::bar_t"]

    .. seealso:: :ref:`type_casters`
    """

    #: Header file to include when one of the types are detected in a wrapper
    header: str

    #: Types to look for to indicate that this type caster header should be
    #: included.
    types: List[str]

    #: If a parameter type that requires this type caster requires a default
    #: argument, a C-style ``(type)`` cast is used on the default argument.
    #:
    #: The default cast can be disabled via param_override's ``disable_type_caster_default_cast``
    default_arg_cast: bool = False


class WrapperConfig(Model):
    """
    Configuration for building a C++ python extension module, optionally
    using autogenerated wrappers around existing library code.

    .. code-block:: toml

       [tool.robotpy-build.wrappers."PACKAGENAME"]
       name = "package_name"

    The PACKAGENAME above is a python package (eg "example.package.name").
    A robotpy-build project can contain many different wrappers and packages.
    """

    #: Name that other projects/wrappers use in their 'depends' list
    name: str

    #: Name of extension to build. If None, set to _{name}
    extension: Optional[str] = None

    #: Name of generated file that ensures the shared libraries and any
    #: dependencies are loaded. Defaults to ``_init{extension}.py``
    #:
    #: Generally, you should create an ``__init__.py`` file that imports
    #: this module, otherwise your users will need to do so.
    libinit: Optional[str] = None

    #: List of robotpy-build library dependencies. This affects this wrapper
    #: library in the following ways:
    #:
    #: * Any include file directories exported by the dependency will be added
    #:   to the include path for any source files compiled by this wrapper
    #: * It will be linked to any libraries the dependency contains
    #: * The python module for the dependency will be imported in the
    #:   ``_init{extension}.py`` file.
    depends: List[str] = []

    #: If this project depends on external libraries stored in a maven repo
    #: specify it here.
    maven_lib_download: Optional[MavenLibDownload] = None

    #: If this project depends on external libraries downloadable from some URL
    #: specify it here
    download: Optional[List[Download]] = None

    #: List of extra include directories to export, relative to the
    #: project root.
    extra_includes: List[str] = []

    #: Optional source files to compile. Path is relative to the root of
    #: the project.
    sources: List[str] = []

    #: Specifies header files that autogenerated pybind11 wrappers will be
    #: created for. Simple C++ headers will most likely 'just work', but
    #: complex headers will need to have an accompanying :attr:`generation_data`
    #: file specified that can customize the autogenerated files.
    #:
    #: List of dictionaries: each dictionary key is used for the function
    #: name of the initialization function, the value is the header that is
    #: being wrapped. The header is first looked for relative to the
    #: package, then relative to each include directory (including
    #: downloaded and extracted packages).
    #:
    #: .. code-block:: toml
    #:
    #:    [tool.robotpy-build.wrappers."PACKAGENAME".autogen_headers]
    #:    Name = "header.h"
    #:
    #: .. seealso:: :ref:`autowrap`
    #:
    autogen_headers: Optional[Dict[str, str]] = None

    #: DEPRECATED: Same as autogen_headers, but more complicated
    generate: Optional[List[Dict[str, str]]] = None

    #: Path to a single data.yml to use during code generation, or a directory
    #: of yaml files. If a directory, generation data will be looked up
    #: using the key in the generate dictionary.
    #:
    #: These YAML files can be generated via the robotpy-build command line tool:
    #:
    #: .. code-block:: sh
    #:
    #:    robotpy-build create-gen --write
    #:
    #: .. seealso:: :ref:`gendata`
    #:
    generation_data: Optional[str] = None

    #: Specifies type casters that this package exports.
    type_casters: List[TypeCasterConfig] = []

    #: Preprocessor definitions to apply when compiling this wrapper.
    pp_defines: List[str] = []

    #: If True, skip this wrapper; typically used in conjection with an override.
    ignore: bool = False


class DistutilsMetadata(Model):
    """
    Configures the metadata that robotpy-build passes to setuptools when
    the project is installed. The keys in this section match the standard
    arguments passed to the ``setuptools.setup`` function.

    .. code-block:: toml

       [tool.robotpy-build.metadata]
       name = "my-awesome-dist"
       description = "Cool thing"
       license = "MIT"

    robotpy-build will automatically detect/set the following keys:

    * cmdclass
    * ext_modules
    * include_package_data - ``True``
    * long_description - Contents of README.md/README.rst
    * long_description_content_type - If required
    * packages
    * python_requires - ``>=3.6``
    * version - via setuptools_scm
    * zip_safe - ``False``

    .. note:: This section is required
    """

    class Config:
        # allow passing in extra keywords to setuptools
        extra = "allow"

    #: The name of the package
    name: str

    #: A single line describing the package
    description: Optional[str] = None

    #: The name of the package author
    author: str

    #: The email address of the package author
    author_email: str

    #: A URL for the package (homepage)
    url: str

    #: The license for the package
    license: str

    #: A string or list of strings specifying what other distributions need
    #: to be installed when this one is.
    install_requires: List[str]


class SupportedPlatform(Model):
    """
    Supported platforms for this project. Currently this information is
    merely advisory, and is used to generate error messages when platform
    specific downloads fail.

    .. code-block:: toml

       [tool.robotpy-build]
       base_package = "my.package"
       supported_platforms = [
           { os = "windows", arch = "x86-64" },
       ]

    .. seealso:: List of supported :ref:`platforms <platforms>`

    """

    #: Platform operating system name
    os: Optional[str] = None

    #: Platform architecture
    arch: Optional[str] = None


class RobotpyBuildConfig(Model):
    """
    Contains information for configuring the project

    .. code-block:: toml

       [tool.robotpy-build]
       base_package = "my.package"

    .. note:: This section is required
    """

    #: Python package to store version information and robotpy-build metadata in
    base_package: str

    #:
    #: .. seealso:: :class:`.SupportedPlatform`
    #:
    supported_platforms: List[SupportedPlatform] = []

    #
    # These are all documented in their class, it's more confusing to document
    # them here too.
    #

    metadata: DistutilsMetadata

    wrappers: Dict[str, WrapperConfig] = {}

    static_libs: Dict[str, StaticLibConfig] = {}
