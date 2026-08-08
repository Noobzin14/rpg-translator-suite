"""Plugin registration service for RPG Translator Suite."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.base_plugin import BasePlugin

LOGGER = logging.getLogger(__name__)


class PluginManager:
    """Maintains the collection of registered engine plugins."""

    def __init__(self, plugin_directory: Path) -> None:
        """Initialize the plugin manager.

        Args:
            plugin_directory: Directory reserved for engine plugin packages.
        """
        self._plugin_directory = plugin_directory
        self._plugins: dict[str, BasePlugin] = {}

    @property
    def plugin_directory(self) -> Path:
        """Return the directory reserved for plugins."""
        return self._plugin_directory

    def ensure_plugin_directory(self) -> None:
        """Create the plugin directory when it does not exist."""
        self._plugin_directory.mkdir(parents=True, exist_ok=True)

    def register(self, plugin: BasePlugin) -> None:
        """Register a plugin instance.

        Args:
            plugin: Plugin instance implementing the base plugin interface.

        Raises:
            ValueError: If another plugin with the same identifier exists.
        """
        if plugin.plugin_id in self._plugins:
            message = f"Plugin already registered: {plugin.plugin_id}"
            LOGGER.error(message)
            raise ValueError(message)

        self._plugins[plugin.plugin_id] = plugin
        LOGGER.info("Plugin registered: %s", plugin.plugin_id)

    def all_plugins(self) -> tuple[BasePlugin, ...]:
        """Return all registered plugins."""
        return tuple(self._plugins.values())
