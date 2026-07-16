"""Tests for the plugin manager."""

from pathlib import Path

import pytest

from app.core.base_plugin import BasePlugin
from app.core.plugin_manager import PluginManager


class DummyPlugin(BasePlugin):
    """Minimal plugin used by plugin manager tests."""

    plugin_id = "dummy"
    display_name = "Dummy"

    def detect(self, project_path: Path) -> bool:
        """Return false because this test plugin supports no projects."""
        return False


def test_plugin_manager_registers_plugin() -> None:
    """PluginManager stores registered plugins."""
    manager = PluginManager(plugin_directory=Path("plugins"))
    plugin = DummyPlugin()

    manager.register(plugin)

    assert manager.all_plugins() == (plugin,)


def test_plugin_manager_rejects_duplicate_plugin_ids() -> None:
    """PluginManager rejects duplicate plugin identifiers."""
    manager = PluginManager(plugin_directory=Path("plugins"))
    manager.register(DummyPlugin())

    with pytest.raises(ValueError):
        manager.register(DummyPlugin())
