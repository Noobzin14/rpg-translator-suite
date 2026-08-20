"""Plugin loading infrastructure for RPG Translator Suite."""

from __future__ import annotations

from pathlib import Path

from app.core.base_plugin import BasePlugin
from app.core.plugin_registry import PluginRegistry


class PluginLoader:
    """Coordinates plugin loading without performing discovery yet."""

    def __init__(self, plugin_directory: Path, registry: PluginRegistry) -> None:
        """Initialize the plugin loader.

        Args:
            plugin_directory: Directory reserved for engine plugin packages.
            registry: Registry receiving loaded plugin instances.
        """
        self._plugin_directory = plugin_directory
        self._registry = registry

    @property
    def plugin_directory(self) -> Path:
        """Return the directory reserved for plugins."""
        return self._plugin_directory

    def ensure_plugin_directory(self) -> None:
        """Create the plugin directory when it does not exist."""
        self._plugin_directory.mkdir(parents=True, exist_ok=True)

    def load_registered_plugins(self) -> tuple[BasePlugin, ...]:
        """Return plugin instances registered in the loader registry."""
        return self._registry.all_plugins()
