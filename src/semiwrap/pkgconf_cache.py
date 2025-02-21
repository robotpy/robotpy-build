import pathlib
import shlex
import typing as T

import pkgconf


INITPY_VARNAME = "pkgconf_pypi_initpy"


class CacheEntry:

    def __init__(self, name: str) -> None:
        self.name = name

    def _get_pkgconf_data(self, *args) -> str:
        r = pkgconf.run_pkgconf(self.name, *args, capture_output=True)
        if r.returncode != 0:
            raise KeyError(f"cannot locate package '{self.name}'")

        return r.stdout.decode("utf-8").strip()

    @property
    def include_path(self) -> T.List[pathlib.Path]:
        """Only the include path for this package"""
        if not hasattr(self, "_include_path"):
            include_path = []
            raw = self._get_pkgconf_data(
                "--cflags-only-I", "--maximum-traverse-depth=1"
            )
            for i in shlex.split(raw):
                assert i.startswith("-I")
                include_path.append(pathlib.Path(i[2:]).absolute())

            self._include_path = include_path

        return self._include_path

    @property
    def full_include_path(self) -> T.List[pathlib.Path]:
        """Include path for this package and requirements"""
        if not hasattr(self, "_full_include_path"):
            full_include_path = []
            raw = self._get_pkgconf_data("--cflags-only-I")
            for i in shlex.split(raw):
                assert i.startswith("-I")
                full_include_path.append(pathlib.Path(i[2:]).absolute())

            self._full_include_path = full_include_path

        return self._full_include_path

    @property
    def type_casters_path(self) -> T.Optional[pathlib.Path]:
        if not hasattr(self, "_type_casters_path"):
            raw = self._get_pkgconf_data("--path")
            pc_path = pathlib.Path(raw)
            type_caster_cfg = pc_path.with_suffix(".pybind11.json")
            if type_caster_cfg.exists():
                self._type_casters_path = type_caster_cfg
            else:
                self._type_casters_path = None

        return self._type_casters_path

    @property
    def libinit_py(self) -> T.Optional[str]:
        if not hasattr(self, "_libinit_py"):
            raw = self._get_pkgconf_data(f"--variable={INITPY_VARNAME}")
            if raw:
                self._libinit_py = raw
            else:
                self._libinit_py = None

        return self._libinit_py


class PkgconfCache:
    def __init__(self) -> None:
        self._cache: T.Dict[str, CacheEntry] = {}

    def get(self, depname: str) -> CacheEntry:
        entry = self._cache.get(depname)
        if entry is None:
            self._cache[depname] = entry = CacheEntry(depname)
        return entry
