"""Tests for the plugin loader infrastructure."""

from app.core.plugin_loader import PluginLoader
from app.core.plugin_registry import PluginRegistry


def test_plugin_loader_ensures_plugin_directory(tmp_path) -> None:
    """PluginLoader creates the plugin directory without discovery."""
    plugin_directory = tmp_path / "plugins"
    loader = PluginLoader(plugin_directory, PluginRegistry())

    loader.ensure_plugin_directory()

    assert plugin_directory.is_dir()
    assert loader.load_registered_plugins() == ()
