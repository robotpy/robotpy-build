# Used by robotpybuild entry point

from os.path import abspath, join, dirname
from typing import Any, Dict, List, Optional

_root = abspath(dirname(__file__))


def get_include_dirs() -> Optional[List[str]]:
    return [join(_root, "pybind11", "include"), join(_root, "include")]


def get_library_dirs() -> Optional[List[str]]:
    pass


def get_type_casters_cfg(casters: Dict[str, Dict[str, Any]]) -> None:
    casters.update(
        {
            # STL support
            "std::vector": {"hdr": "pybind11/stl.h"},
            "std::deque": {"hdr": "pybind11/stl.h"},
            "std::list": {"hdr": "pybind11/stl.h"},
            "std::array": {"hdr": "pybind11/stl.h"},
            "std::valarray": {"hdr": "pybind11/stl.h"},
            "std::set": {"hdr": "pybind11/stl.h"},
            "std::map": {"hdr": "pybind11/stl.h"},
            "std::unordered_map": {"hdr": "pybind11/stl.h"},
            "std::optional": {"hdr": "pybind11/stl.h"},
            "std::nullopt_t": {"hdr": "pybind11/stl.h"},
            "std::variant": {"hdr": "pybind11/stl.h"},
            "std::function": {"hdr": "pybind11/functional.h"},
            "std::complex": {"hdr": "pybind11/complex.h"},
            "std::chrono::duration": {"hdr": "pybind11/chrono.h"},
            "std::chrono::time_point": {"hdr": "pybind11/chrono.h"},
            # Eigen support (requires numpy)
            "Eigen::Block": {"hdr": "pybind11/eigen.h"},
            "Eigen::DiagonalMatrix": {"hdr": "pybind11/eigen.h"},
            "Eigen::Matrix": {"hdr": "pybind11/eigen.h"},
            "Eigen::MatrixXd": {"hdr": "pybind11/eigen.h"},
            "Eigen::MatrixXdR": {"hdr": "pybind11/eigen.h"},
            "Eigen::MatrixXi": {"hdr": "pybind11/eigen.h"},
            "Eigen::MatrixXf": {"hdr": "pybind11/eigen.h"},
            "Eigen::Ref": {"hdr": "pybind11/eigen.h"},
            "Eigen::Matrix4d": {"hdr": "pybind11/eigen.h"},
            "Eigen::RowVectorXf": {"hdr": "pybind11/eigen.h"},
            "Eigen::SparseMatrix": {"hdr": "pybind11/eigen.h"},
            "Eigen::SparseView": {"hdr": "pybind11/eigen.h"},
            "Eigen::Vector": {"hdr": "pybind11/eigen.h"},
            "Eigen::VectorXf": {"hdr": "pybind11/eigen.h"},
            "Eigen::VectorXcf": {"hdr": "pybind11/eigen.h"},
        }
    )


def get_type_casters(casters: Dict[str, str]) -> None:
    t = {}
    get_type_casters_cfg(t)
    for k, v in t.items():
        if "hdr" in v:
            casters[k] = v["hdr"]
