Building on macOS
=================

macOS handles library files differently than Windows or Linux. macOS will not
automatically find and link libraries at runtime. Rather, libraries need to be
linked beforehand.

For now, look at https://github.com/robotpy/pyntcore as an example.

Modify pyproject.toml
---------------------

### Prerequisite

Libraries downloaded when building are defined by `libs`.
```toml
libs = ["ntcore"]
```

External libraries required are defined by `depends`.
```toml
depends = ["wpiutil"]
```

### Modifications

To assist macOS in finding libraries, add a
`tool.robotpy-build.macos_lib_locations` sections. The keys and values here
define the paths to libraries.

```toml
[tool.robotpy-build.macos_lib_locations]
"libwpiutil.dylib" = "wpiutil/lib/libwpiutil.dylib"
```

#### Relative Paths

This path is relative to to the parent of the package directory. Usually, the
parent of the package directory is your site-packages folder. In the example,
(on my system) `"wpiutil/lib/libwpiutil.dylib"` resolves to
`".../site-packages/wpiutil/lib/libwpiutil.dylib"`.

#### Absolute Paths

Absolute paths can also be sepcified. Absolute paths must be bookended by an
`@`. For example, `"@/Users/FakeUser/Desktop/libfake.dylib@"` resolves as is
to `"/Users/FakeUser/Desktop/libfake.dylib/"`.

Note: Do not treat a relative path as an absolute path. In most cases, it
will fail.

Automatic Library Detection
---------------------------

Paths to internal libraries (usually defined in `libs`) are automatically
detected. Paths to these libraries do not have to be defined. If a path to
an internal library is defined, it will override the automatically found path.

Building in Developer Mode
--------------------------
### Path Resolution

When building in developer mode (`python setup.py develop` or `pip install -e`),
automatic library detection will fail. Paths to all libraries need to be defined.
Furthermore, resolution of relative paths may also fail. For guaranteed path
resolution, use absolute paths when building in developer mode.

Note: All packages depending on a library provided by your package will also
need their paths updated.

### Relink Tool

If your package is built in developer mode, then other package may fail to
find/link to your package's libraries. You will need to relink the libraries of
dependent packages.

To relink the libraries of dependent packages, rather than rebuild those
packages, you can use the relink-libraries tool.

```bash
python -m robotpy_build relink-libraries "libraries" "dependents"
```

`"libraries"` is the path to the folder containing `*.dylib` files.

`"dependents"` is the path to the folder containing files that need to be fixed
(have their dependecies relinked).

For example,
```bash
python -m robotpy_build relink-libraries ./robotpy-wpiutil ./pyntcore
```
1. finds all libraries (`*.dylib`) in `./robotpy-wpiutil`
2. finds all dependencies for all (`*.so` and `*.dylib`) files in `./pyntcore`
3. Relinks dependencies to libraries

Note: This tool finds libraries and dependencies recursively. You do not need
to specify very-specific paths (the above example does not either). However,
the shallower the path, the longer the runtime.

Subnote: If your library/dependency path contain multiple venvs, undesired
libraries may be relinked.

### Easy Workflow

Understandably, you may not want to spend time relinking sepcific libraries as
you are working. This is a suggested workflow to minimize manual relinking
efforts.

Setup your workspace as (example):

```
workspace/
├── venv/               <- Your virtualenv
├── robotpy-build/
├── robotpy-wpiutil/
└── robotpy-pyntcore/   <- Ex. A package you are developing
```

Then, to relink libraries after a rebuild, run:
```bash
workspace/ $ python -m robotpy_build relink-libraries . .
```

This will fix all dependencies.

Note: The runtime of this workflow is higher than specifying more specific paths.