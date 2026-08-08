"""Configuration management for RPG Translator Suite."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ConfigManager:
    """Stores application configuration values in memory.

    Persistence is intentionally not implemented in Sprint 0.1 so the
    foundation stays independent from storage choices and future settings
    formats.
    """

    def __init__(self, base_path: Path) -> None:
        """Initialize the configuration manager.

        Args:
            base_path: Root directory used as the application base path.
        """
        self._base_path = base_path
        self._values: dict[str, Any] = {}

    @property
    def base_path(self) -> Path:
        """Return the application base path."""
        return self._base_path

    def get(self, key: str, default: Any | None = None) -> Any | None:
        """Return a configuration value.

        Args:
            key: Configuration key.
            default: Value returned when the key is not configured.
        """
        return self._values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Store a configuration value.

        Args:
            key: Configuration key.
            value: Value to store.
        """
        self._values[key] = value

    def remove(self, key: str) -> None:
        """Remove a configuration value when it exists."""
        self._values.pop(key, None)

    def contains(self, key: str) -> bool:
        """Return whether a configuration key is configured."""
        return key in self._values
