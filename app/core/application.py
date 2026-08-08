"""Application bootstrap services for RPG Translator Suite."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.config_manager import ConfigManager
from app.core.logger import configure_logging
from app.core.plugin_manager import PluginManager

LOGGER = logging.getLogger(__name__)


class Application:
    """Coordinates the engine-independent application foundation."""

    def __init__(self, base_path: Path) -> None:
        """Initialize core services.

        Args:
            base_path: Repository or installation root path.
        """
        self.base_path = base_path
        self.config = ConfigManager(base_path=base_path)
        self.plugins = PluginManager(plugin_directory=base_path / "plugins")

    def initialize(self) -> None:
        """Initialize application services required at startup."""
        configure_logging(self.base_path / "resources" / "logs")
        self.plugins.ensure_plugin_directory()
        LOGGER.info("RPG Translator Suite initialized")
