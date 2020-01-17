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

If you forget an external dependency, the library won't load.

Automatic Library Detection
---------------------------

Paths to robotpy-build provided libraries (usually defined in `libs`) are automatically
detected. Paths to these libraries do not have to be defined. If a path to
an internal library is defined, it will override the automatically found path.

TODO: deal with other non-system libraries
