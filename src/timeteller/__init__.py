__all__ = ("__version__", "ext", "stdlib")

from importlib import metadata
from typing import TYPE_CHECKING

__version__ = metadata.version(__name__)


if TYPE_CHECKING:
    from timeteller import ext, stdlib


def __getattr__(name: str):
    # Lazy import of submodules on attribute access (PEP 562)
    if name in __all__:
        import importlib

        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    # Improve interactive discoverability
    items = __all__ + tuple(globals().keys())
    exclude = {"metadata", "TYPE_CHECKING"}
    return sorted(item for item in items if item not in exclude)
