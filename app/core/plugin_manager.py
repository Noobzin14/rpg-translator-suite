"""Plugin coordination service for RPG Translator Suite."""

from __future__ import annotations

from pathlib import Path

from app.core.base_plugin import BasePlugin
from app.core.plugin_loader import PluginLoader
from app.core.plugin_registry import PluginRegistry
from app.core.plugin_state import PluginState


class PluginManager:
    """Coordinates plugin registration and loading boundaries."""

    def __init__(
        self,
        plugin_directory: Path,
        registry: PluginRegistry | None = None,
        loader: PluginLoader | None = None,
    ) -> None:
        """Initialize the plugin manager.

        Args:
            plugin_directory: Directory reserved for engine plugin packages.
            registry: Optional plugin registry used for storage and queries.
            loader: Optional plugin loader used for loading infrastructure.
        """
        self._registry = registry or PluginRegistry()
        self._loader = loader or PluginLoader(
            plugin_directory=plugin_directory,
            registry=self._registry,
        )

    @property
    def plugin_directory(self) -> Path:
        """Return the directory reserved for plugins."""
        return self._loader.plugin_directory

    def ensure_plugin_directory(self) -> None:
        """Create the plugin directory when it does not exist."""
        self._loader.ensure_plugin_directory()

    def register(self, plugin: BasePlugin) -> None:
        """Register a plugin instance through the registry."""
        self._registry.register(plugin)

    def get(self, plugin_id: str) -> BasePlugin | None:
        """Return a registered plugin by identifier, if present."""
        return self._registry.get(plugin_id)

    def all_plugins(self) -> tuple[BasePlugin, ...]:
        """Return all registered plugins."""
        return self._registry.all_plugins()

    def state_of(self, plugin_id: str) -> PluginState | None:
        """Return the lifecycle state for a registered plugin."""
        return self._registry.state_of(plugin_id)
