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


def test_plugin_loader_returns_registered_plugins(tmp_path) -> None:
    """PluginLoader exposes plugins registered by the PluginRegistry."""
    from plugins.rpgmaker_mv import RPGMakerMVPlugin

    registry = PluginRegistry()
    plugin = RPGMakerMVPlugin()
    registry.register(plugin)
    loader = PluginLoader(tmp_path / "plugins", registry)

    assert loader.load_registered_plugins() == (plugin,)
