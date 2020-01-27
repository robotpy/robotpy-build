Writing your own wrappers
=========================

robotpy-build is designed to make this super easy! Soon we will have an example
project, but for now look at https://github.com/robotpy/pyntcore

First, install all of your packages dependencies. If your package has binary
dependencies and they aren't wrapped by robotpy-build, start with wrapping
those first.

Define pyproject.toml
---------------------

Create a `pyproject.toml` for your new project. The schema for the TOML file
can be found at [pyproject_configs.py](../robotpy_build/pyproject_configs.py).

The `tool.robotpy-build.metadata` section matches the standard arguments to
the setuptools.setup function.

### Add downloads

If you're wrapping an FRC library, add a `maven_lib_download` section.
The metadata in this section corresponds to whatever is in the vendor
JSON file.

    [tool.robotpy-build.wrappers."myproject".maven_lib_download]
    artifact_id = "ntcore-cpp"
    group_id = "edu.wpi.first.ntcore"
    repo_url = "https://frcmaven.wpi.edu/artifactory/release"
    version = "2020.1.2"

    # This is the name of the library contained in the download
    libs = ["ntcore"]

### Define wrapper section

A wrapper section might look like this:

    [tool.robotpy-build.wrappers."myproject"]
    name = "myproject"
    sources = ["myproject/src/myproject.cpp"]

If wrapping a downloaded library, run `python setup.py build_dl` to
download your library. You can also wrap sources in your own wrapper.

`python -m robotpy_build scan_headers` will scan all of your defined
includes directories (including those of downloaded artifacts) and
output something you can paste into the `generate` key. Edit those.

`python -m robotpy_build create-gen` will scan your defined generate
items and output yaml for them in the directory defined by `generation_data`.
Use the `--write` argument to write the files, it won't overwrite existing
files. See below for editing them.

WrapperConfig defines other things you can do.

Customizing the wrapper generation
----------------------------------

The wrapper YAML file schema is defined in [hooks_datacfg.py](../robotpy-build/hooks_datacfg.py).

### Common errors

> error: invalid use of incomplete type

pybind11 requires you to use complete types when binding an object. Typically
this means that somewhere in the header there was a forward declaration:

    class Foo;

Foo is defined in some header, but not the header you're scanning. To fix it,
tell the generator to include the header:

    extra_includes:
    - path/to/Foo.h

> 'error: 'SomeEnum' has not been declared'

Often this is referring to a parameter type or a default argument. You can use
the 'param_override' setting for that function to fix it.


> unresolved external symbol PyInit__XXX

You forgot to include the pybind11 entrypoint in your sources. Here's how you
do it:

    #include <rpygen_wrapper.hpp>

    RPYBUILD_PYBIND11_MODULE(m) {
        initWrapper(m);
    }

You can of course put other content in here if needed.

Building
--------

Start out by doing `python setup.py develop`.

To save yourself time, there are some techniques to make the development
process faster. Ideally, you'll start out on a Linux system.

First, install ccache. 

Second, define these environment variables:

    export RPYBUILD_PARALLEL=1
    export CC="ccache gcc"
    export CXX="ccache g++"
    export GCC_COLORS=1

The first one will make robotpy-build compile in parallel. The second tells
setuptools to use ccache, and the third makes error output nice when using
ccache.

When developing wrappers of very large projects, the wrapper regeneration step
can take a very long time. Often you find that you only want to modify a single
file. You can define a YAML file and tell robotpy-build to only regenerate the
output for that single file, instead of scanning all files and regenerating
everything.

Create a filter.yml:

    ---

    # the names in this list correspond to the keys in your 'generate' section
    only_generate:
    - SendableChooser

Then do:

    RPYBUILD_GEN_FILTER=filter.yml python setup.py develop

Platform-specific dependencies
------------------------------

You can define 'override' sections that will be grafted onto the configuration
if they match a particular platform. For example, to change the dependencies
for a wrapper section on Windows:

    [tool.robotpy-build.wrappers."myproject".override.os_windows]
    depends = ["windows-thing"]

See `overrides.py` for more information about how overrides are applied.

Run `robotpy-build platform-info` for platform specific keys and available
override keys.
