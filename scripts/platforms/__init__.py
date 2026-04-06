"""Platform plugins for fetching user context.

Each module in this package must define:
    NAME: str           — display name
    DESCRIPTION: str    — shown in help (?)
    detect(url) -> bool — does this URL belong to this platform?
    fetch(url, cache_dir) -> str — fetch content, return text
"""

import importlib
import pkgutil
from pathlib import Path


def _load_plugins() -> list:
    plugins = []
    pkg_path = Path(__file__).parent
    for info in pkgutil.iter_modules([str(pkg_path)]):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module(f".{info.name}", __package__)
        if hasattr(mod, "detect") and hasattr(mod, "fetch"):
            plugins.append(mod)
    # Sort by NAME for consistent ordering
    plugins.sort(key=lambda m: getattr(m, "NAME", m.__name__))
    return plugins


def get_plugins() -> list:
    return _load_plugins()


def detect_platform(url: str):
    """Return the first plugin that matches this URL, or None."""
    for plugin in get_plugins():
        if plugin.detect(url):
            return plugin
    return None
