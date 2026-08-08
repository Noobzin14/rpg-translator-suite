"""Tests for the plugin registry."""

from pathlib import Path

import pytest

from app.core.base_plugin import BasePlugin
from app.core.exceptions import PluginRegistrationError
from app.core.plugin_registry import PluginRegistry
from app.core.plugin_state import PluginState


class DummyPlugin(BasePlugin):
    """Minimal plugin used by plugin registry tests."""

    plugin_id = "dummy"
    display_name = "Dummy"

    def detect(self, project_path: Path) -> bool:
        """Return false because this test plugin supports no projects."""
        return False


def test_plugin_registry_registers_and_returns_plugin() -> None:
    """PluginRegistry stores registered plugins and their initial state."""
    registry = PluginRegistry()
    plugin = DummyPlugin()

    registry.register(plugin)

    assert registry.get("dummy") is plugin
    assert registry.all_plugins() == (plugin,)
    assert registry.state_of("dummy") is PluginState.REGISTERED


def test_plugin_registry_rejects_duplicate_plugin_ids() -> None:
    """PluginRegistry rejects duplicate plugin identifiers."""
    registry = PluginRegistry()
    registry.register(DummyPlugin())

    with pytest.raises(PluginRegistrationError):
        registry.register(DummyPlugin())


def test_plugin_registry_updates_state_for_registered_plugin() -> None:
    """PluginRegistry updates states only for known plugins."""
    registry = PluginRegistry()
    registry.register(DummyPlugin())

    registry.set_state("dummy", PluginState.LOADED)

    assert registry.state_of("dummy") is PluginState.LOADED


def test_plugin_registry_rejects_state_for_unknown_plugin() -> None:
    """PluginRegistry rejects state changes for unknown plugins."""
    registry = PluginRegistry()

    with pytest.raises(PluginRegistrationError):
        registry.set_state("missing", PluginState.ERROR)
