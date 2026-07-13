from importlib.metadata import PackageNotFoundError, version

from .server import main, mcp

try:
    __version__ = version("apolo-mcp")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["__version__", "main", "mcp"]
