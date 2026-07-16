"""Tests for the configuration manager."""

from pathlib import Path

from app.core.config_manager import ConfigManager


def test_config_manager_stores_values() -> None:
    """ConfigManager stores and retrieves in-memory values."""
    manager = ConfigManager(base_path=Path("/tmp/rts"))

    manager.set("language", "en")

    assert manager.get("language") == "en"
    assert manager.get("missing", "fallback") == "fallback"
