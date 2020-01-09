from distutils.util import get_platform as _get_platform
from typing import NamedTuple


# wpilib platforms at https://github.com/wpilibsuite/native-utils/blob/master/src/main/java/edu/wpi/first/nativeutils/WPINativeUtilsExtension.java
class WPILibMavenPlatform(NamedTuple):
    os: str
    arch: str
    libprefix: str

    #: runtime linkage
    libext: str

    #: compile time linkage
    linkext: str


# key is python platform, value is information about wpilib maven artifacts
_platforms = {
    # TODO: this isn't always true
    "linux-armv7l": WPILibMavenPlatform("linux", "athena", "lib", ".so", ".so"),
    "linux-x86_64": WPILibMavenPlatform("linux", "x86-64", "lib", ".so", ".so"),
    # TODO: linuxraspbian
    "win32": WPILibMavenPlatform("windows", "x86", "", ".dll", ".lib"),
    "win-amd64": WPILibMavenPlatform("windows", "x86-64", "", ".dll", ".lib"),
    # TODO: need to filter this value
    "macosx-10.9-x86_64": WPILibMavenPlatform(
        "osx", "x86-64", "lib", ".dylib", ".dylib"
    ),
}


def get_platform() -> WPILibMavenPlatform:
    """
        Retrieve platform specific information
    """

    # TODO: _PYTHON_HOST_PLATFORM is used for cross builds,
    #       and is returned directly from get_platform. Might
    #       be useful to note for the future.

    pyplatform = _get_platform()
    try:
        return _platforms[pyplatform]
    except KeyError:
        raise KeyError(f"platform {pyplatform} is not supported by robotpy-build!")
