"""
Top-level version information for sarif-tools.
"""
import importlib.metadata


def _read_package_version():
    try:
        return importlib.metadata.version("sarif-tools")
    except importlib.metadata.PackageNotFoundError:
        return "local"


__version__ = _read_package_version()
