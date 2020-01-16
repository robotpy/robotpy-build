Building on macOS
=================

macOS handles library files differently than Windows or Linux. macOS will not
automatically find and link libraries at runtime. Rather, libraries need to be
linked beforehand.

For now, look at https://github.com/robotpy/pyntcore as an example.

Modify pyproject.toml
---------------------

### Existing

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

Note: Do not treat a relative path as an absolute path. In most cases, this
will fail.

Automatic Library Detection
---------------------------

Paths to internal libraries (usually defined in `libs`) are automatically
detected. Paths to these libraries do not have to be defined. If a path to
an internal library is defined, it will override the automatically found path.

Building in Developer Mode
--------------------------

When building in developer mode (`python setup.py develop` or `pip install -e`),
automatic library detection will fail. Paths to all libraries need to be defined.
Furthmore, resolution of relative paths may also fail. For guaranteed path
resolution, use absolute paths when building in developer mode.

Note: All packages depending on a library provided by your package will also
need their paths updated.

