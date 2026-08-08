"""Plugin registry for RPG Translator Suite."""

from __future__ import annotations

import logging

from app.core.base_plugin import BasePlugin
from app.core.exceptions import PluginRegistrationError
from app.core.plugin_state import PluginState

LOGGER = logging.getLogger(__name__)


class PluginRegistry:
    """Stores registered plugins and their lifecycle states."""

    def __init__(self) -> None:
        """Initialize an empty plugin registry."""
        self._plugins: dict[str, BasePlugin] = {}
        self._states: dict[str, PluginState] = {}

    def register(self, plugin: BasePlugin) -> None:
        """Register a plugin instance.

        Args:
            plugin: Plugin instance implementing the base plugin interface.

        Raises:
            PluginRegistrationError: If the plugin identifier already exists.
        """
        if plugin.plugin_id in self._plugins:
            message = f"Plugin already registered: {plugin.plugin_id}"
            LOGGER.error(message)
            raise PluginRegistrationError(message)

        self._plugins[plugin.plugin_id] = plugin
        self._states[plugin.plugin_id] = PluginState.REGISTERED
        LOGGER.info("Plugin registered: %s", plugin.plugin_id)

    def get(self, plugin_id: str) -> BasePlugin | None:
        """Return a registered plugin by identifier, if present."""
        return self._plugins.get(plugin_id)

    def all_plugins(self) -> tuple[BasePlugin, ...]:
        """Return all registered plugins."""
        return tuple(self._plugins.values())

    def state_of(self, plugin_id: str) -> PluginState | None:
        """Return the lifecycle state for a registered plugin."""
        return self._states.get(plugin_id)

    def set_state(self, plugin_id: str, state: PluginState) -> None:
        """Update the lifecycle state for a registered plugin.

        Raises:
            PluginRegistrationError: If the plugin identifier is unknown.
        """
        if plugin_id not in self._plugins:
            message = f"Plugin is not registered: {plugin_id}"
            LOGGER.error(message)
            raise PluginRegistrationError(message)

        self._states[plugin_id] = state
