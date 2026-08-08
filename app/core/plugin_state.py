"""Plugin lifecycle state definitions."""

from __future__ import annotations

from enum import StrEnum


class PluginState(StrEnum):
    """Basic lifecycle states for plugins known by the core."""

    REGISTERED = "registered"
    LOADED = "loaded"
    ERROR = "error"
