"""Integration tests for RPG Maker MV data extraction."""

import json
from pathlib import Path

import pytest

from app.core.plugin_manager import PluginManager
from app.core.project_detector import ProjectDetector
from app.core.project_extractor import ProjectExtractor
from app.core.project_loader import ProjectLoader
from app.core.project_model import Project, ProjectLoadStatus
from app.core.plugin_registry import PluginRegistry
from plugins.rpgmaker_mv.plugin import RPGMakerMVPlugin


@pytest.fixture
def mv_plugin():
    """Create an RPG Maker MV plugin instance."""
    return RPGMakerMVPlugin()


@pytest.fixture
def plugin_manager_with_mv(tmp_path, mv_plugin):
    """Create a plugin manager with MV plugin registered."""
    registry = PluginRegistry()
    registry.register(mv_plugin)
    return PluginManager(plugin_directory=tmp_path / "plugins", registry=registry)


@pytest.fixture
def minimal_mv_project(tmp_path):
    """Create a minimal RPG Maker MV project fixture."""
    # Create directory structure
    www_data = tmp_path / "www" / "data"
    www_data.mkdir(parents=True)
    www_js = tmp_path / "www" / "js"
    www_js.mkdir(parents=True)

    # Create package.json
    package_json = {
        "name": "test-mv-game",
        "version": "1.0.0",
        "dependencies": {
            "rpg_core": "^1.0.0"
        }
    }
    (tmp_path / "package.json").write_text(json.dumps(package_json), encoding="utf-8")

    # Create System.json with game title
    system_json = {
        "gameTitle": "Test Game Title",
        "locale": "en_US",
        "partyMembers": [1],
    }
    (www_data / "System.json").write_text(json.dumps(system_json), encoding="utf-8")

    # Create minimal rpg_core.js
    (www_js / "rpg_core.js").write_text(
        "// RPG Maker MV v1.6.1\nvar SceneManager = {};",
        encoding="utf-8"
    )

    return tmp_path


class TestRPGMakerMVExtraction:
    """Integration tests for RPG Maker MV extraction."""

    def test_extract_game_title_from_system_json(
        self, mv_plugin, minimal_mv_project
    ):
        """Test extracting game title from System.json."""
        # Manually create a loaded project for extraction test
        project = Project(
            path=minimal_mv_project,
            engine="rpgmaker_mv",
            engine_display_name="RPG Maker MV",
            status=ProjectLoadStatus.LOADED,
        )

        result = mv_plugin.extract_data(project)
        
        assert result.status.value == "extracted"
        assert len(result.entries) >= 1
        
        # Find the game title entry
        game_title_entries = [
            e for e in result.entries 
            if e.entry_id == "system:game_title"
        ]
        assert len(game_title_entries) == 1
        assert game_title_entries[0].text == "Test Game Title"
        assert game_title_entries[0].source_path == Path("www/data/System.json")
        assert game_title_entries[0].metadata["field"] == "gameTitle"

    def test_extract_project_name_from_package_json(
        self, mv_plugin, minimal_mv_project
    ):
        """Test extracting project name from package.json."""
        from app.core.project_model import Project, ProjectMetadata
        
        project = Project(
            path=minimal_mv_project,
            engine="rpgmaker_mv",
            engine_display_name="RPG Maker MV",
            status=ProjectLoadStatus.LOADED,
        )

        result = mv_plugin.extract_data(project)
        
        # Find the project name entry
        project_name_entries = [
            e for e in result.entries 
            if e.entry_id == "system:project_name"
        ]
        assert len(project_name_entries) == 1
        assert project_name_entries[0].text == "test-mv-game"
        assert project_name_entries[0].source_path == Path("package.json")

    def test_extract_both_entries(self, mv_plugin, minimal_mv_project):
        """Test extracting both game title and project name."""
        from app.core.project_model import Project
        
        project = Project(
            path=minimal_mv_project,
            engine="rpgmaker_mv",
            status=ProjectLoadStatus.LOADED,
        )

        result = mv_plugin.extract_data(project)
        
        assert result.status.value == "extracted"
        assert len(result.entries) == 2
        
        entry_ids = {e.entry_id for e in result.entries}
        assert "system:game_title" in entry_ids
        assert "system:project_name" in entry_ids

    def test_extract_missing_system_json(self, mv_plugin, tmp_path):
        """Test extraction when System.json is missing."""
        # Create minimal structure without System.json
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "test-game"}),
            encoding="utf-8"
        )
        
        project = Project(
            path=tmp_path,
            engine="rpgmaker_mv",
            status=ProjectLoadStatus.LOADED,
        )

        result = mv_plugin.extract_data(project)
        
        # Should have error about missing file
        assert any(e.code == "missing_file" for e in result.errors)

    def test_extract_invalid_json(self, mv_plugin, tmp_path):
        """Test extraction with invalid JSON file."""
        # Create invalid System.json
        www_data = tmp_path / "www" / "data"
        www_data.mkdir(parents=True)
        (www_data / "System.json").write_text("{ invalid json }", encoding="utf-8")
        
        project = Project(
            path=tmp_path,
            engine="rpgmaker_mv",
            status=ProjectLoadStatus.LOADED,
        )

        result = mv_plugin.extract_data(project)
        
        # Should have error about invalid JSON
        assert any(e.code == "invalid_json" for e in result.errors)

    def test_extract_paths_are_relative(self, mv_plugin, minimal_mv_project):
        """Test that extracted paths are relative, not absolute."""
        from app.core.project_model import Project
        
        project = Project(
            path=minimal_mv_project,
            engine="rpgmaker_mv",
            status=ProjectLoadStatus.LOADED,
        )

        result = mv_plugin.extract_data(project)
        
        for entry in result.entries:
            # Ensure paths are relative (don't start with / or contain drive letters)
            assert not entry.source_path.is_absolute(), \
                f"Entry {entry.entry_id} has absolute path: {entry.source_path}"

    def test_extract_readonly_no_modification(self, mv_plugin, minimal_mv_project):
        """Test that extraction is read-only and doesn't modify files."""
        from app.core.project_model import Project
        
        # Record original file contents
        system_content = (minimal_mv_project / "www" / "data" / "System.json").read_text()
        package_content = (minimal_mv_project / "package.json").read_text()
        
        project = Project(
            path=minimal_mv_project,
            engine="rpgmaker_mv",
            status=ProjectLoadStatus.LOADED,
        )

        mv_plugin.extract_data(project)
        
        # Verify files were not modified
        assert (minimal_mv_project / "www" / "data" / "System.json").read_text() == system_content
        assert (minimal_mv_project / "package.json").read_text() == package_content

    def test_full_integration_extraction(
        self, plugin_manager_with_mv, minimal_mv_project
    ):
        """Test full integration: detection -> loading -> extraction."""
        # Create detector and loader using the plugin manager's internal loader
        from app.core.plugin_loader import PluginLoader
        
        # Get the loader from plugin manager (it has one internally)
        plugin_loader = plugin_manager_with_mv._loader
        
        detector = ProjectDetector(plugin_loader=plugin_loader)
        loader = ProjectLoader(detector=detector, plugin_manager=plugin_manager_with_mv)
        extractor = ProjectExtractor(plugin_manager=plugin_manager_with_mv)
        
        # Detect
        detection = detector.detect(minimal_mv_project)
        assert detection.detected
        
        # Load
        load_result = loader.load(minimal_mv_project)
        assert load_result.project is not None
        assert load_result.project.status == ProjectLoadStatus.LOADED
        
        # Extract
        result = extractor.extract(load_result.project)
        
        # Verify extraction worked
        assert result.status.value in ("extracted", "partial")
        assert len(result.entries) >= 1
        assert result.project is not None
