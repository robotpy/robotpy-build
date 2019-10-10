from distutils.util import get_platform as _get_platform
from collections import namedtuple


# wpilib platforms at https://github.com/wpilibsuite/native-utils/blob/master/src/main/java/edu/wpi/first/nativeutils/WPINativeUtilsExtension.java

WPILibMavenPlatform = namedtuple(
    "WPILibMavenPlatform", ["os", "arch", "libprefix", "libext"]
)

# key is python platform, value is information about wpilib maven artifacts
_platforms = {
    # TODO: this isn't always true
    "linux-armv7l": WPILibMavenPlatform("linux", "athena", "lib", ".so"),
    "linux-x86_64": WPILibMavenPlatform("linux", "x86-64", "lib", ".so"),
    # TODO: linuxraspbian
    "win32": WPILibMavenPlatform("windows", "x86", "", ".dll"),
    "win-amd64": WPILibMavenPlatform("windows", "x86-64", "", ".dll"),
    # TODO: need to filter this value
    "macosx-10.9-x86_64": WPILibMavenPlatform("osx", "x86-64", "lib", ".dylib"),
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

