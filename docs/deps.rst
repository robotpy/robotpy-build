External dependencies
=====================

Download files
--------------

Used to download files from an arbitrary URL. This can download headers,
shared/static libraries, and sources.

.. code-block:: toml

    [[tool.robotpy-build.wrappers."PACKAGENAME".download]]
    url = "https://my/url/something.zip"
    incdir = "include"
    libs = ["mylib"]
    libdir = "libpath"

That tells robotpy-build:

* To download the zipfile at that URL
* Anything in the "include" directory will be extracted to the include path
  for the wrapper
* Libraries will be searched in the "libpath" directory (default is "")
* The shared library "mylib" will be linked to the python module being built

Maven artifacts
---------------

Used to download artifacts from a maven repository. This can download headers,
shared libraries, and sources.

.. code-block:: toml

    [tool.robotpy-build.wrappers."PACKAGENAME".maven_lib_download]
    artifact_id = "mything"
    group_id = "com.example.thing"
    repo_url = "http://example.com/maven"
    version = "1.2.3"

When robotpy-build downloads an artifact from a maven repo, it will unpack it
into a temporary directory and add the relevant directories to your package's
include/library paths. Additionally, any headers will automatically be copied
into your wheel so that other packages can utilize them when linking to your
wheel.

For development purposes, you can download/extract the files locally by
running ``python3 setup.py build_dl``.

.. seealso:: Reference for all :class:`.MavenLibDownload` options

.. note:: It's possible that the archive format is specific to FIRST Robotics.
          If you're trying to use this and it isn't working, file a bug on
          github!

          For FIRST Robotics related projects, the metadata for
          ``maven_lib_download`` can be found in a vendor JSON file.

