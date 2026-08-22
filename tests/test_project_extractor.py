"""Tests for the ProjectExtractor orchestration."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.core.extraction import (
    ExtractionEntry,
    ExtractionEntryType,
    ExtractionIssue,
    ExtractionIssueSeverity,
    ExtractionResult,
    ExtractionStatus,
)
from app.core.plugin_manager import PluginManager
from app.core.project_extractor import ProjectExtractor
from app.core.project_model import Project, ProjectLoadStatus


@pytest.fixture
def plugin_manager():
    """Create a mock plugin manager."""
    return Mock(spec=PluginManager)


@pytest.fixture
def extractor(plugin_manager):
    """Create a ProjectExtractor with mock plugin manager."""
    return ProjectExtractor(plugin_manager)


@pytest.fixture
def loaded_project(tmp_path):
    """Create a loaded project fixture."""
    return Project(
        path=tmp_path,
        engine="test_engine",
        engine_display_name="Test Engine",
        status=ProjectLoadStatus.LOADED,
    )


class TestProjectExtractorInvalidProject:
    """Tests for invalid project states."""

    def test_extract_incomplete_project(self, extractor, tmp_path):
        """Test extraction on an incomplete project."""
        project = Project(
            path=tmp_path,
            engine="test_engine",
            status=ProjectLoadStatus.INCOMPLETE,
        )
        result = extractor.extract(project)
        assert result.status == ExtractionStatus.INVALID_PROJECT
        assert len(result.errors) == 1
        assert result.errors[0].code == "invalid_project_state"
        assert result.project is project

    def test_extract_not_loaded_project(self, extractor, tmp_path):
        """Test extraction on a not loaded project."""
        project = Project(
            path=tmp_path,
            engine="test_engine",
            status=ProjectLoadStatus.NOT_LOADED,
        )
        result = extractor.extract(project)
        assert result.status == ExtractionStatus.INVALID_PROJECT
        assert len(result.errors) == 1

    def test_extract_invalid_path_project(self, extractor, tmp_path):
        """Test extraction on a project with invalid path status."""
        project = Project(
            path=tmp_path,
            engine="test_engine",
            status=ProjectLoadStatus.INVALID_PATH,
        )
        result = extractor.extract(project)
        assert result.status == ExtractionStatus.INVALID_PROJECT


class TestProjectExtractorUnknownEngine:
    """Tests for unknown engine scenarios."""

    def test_extract_project_without_engine(self, extractor, tmp_path):
        """Test extraction on a project with no engine."""
        project = Project(
            path=tmp_path,
            engine=None,
            status=ProjectLoadStatus.LOADED,
        )
        result = extractor.extract(project)
        assert result.status == ExtractionStatus.NOT_SUPPORTED
        assert len(result.errors) == 1
        assert result.errors[0].code == "unknown_engine"


class TestProjectExtractorPluginNotFound:
    """Tests for plugin not found scenarios."""

    def test_extract_plugin_not_found(self, extractor, plugin_manager, loaded_project):
        """Test extraction when plugin is not found."""
        plugin_manager.get.return_value = None
        result = extractor.extract(loaded_project)
        assert result.status == ExtractionStatus.NOT_SUPPORTED
        assert len(result.errors) == 1
        assert result.errors[0].code == "plugin_not_found"
        plugin_manager.get.assert_called_once_with("test_engine")


class TestProjectExtractorPluginNotSupported:
    """Tests for plugins that don't support extraction."""

    def test_extract_plugin_returns_not_supported(
        self, extractor, plugin_manager, loaded_project
    ):
        """Test extraction when plugin returns NOT_SUPPORTED."""
        mock_plugin = Mock()
        mock_plugin.extract_data.return_value = ExtractionResult(
            status=ExtractionStatus.NOT_SUPPORTED
        )
        plugin_manager.get.return_value = mock_plugin

        result = extractor.extract(loaded_project)
        assert result.status == ExtractionStatus.NOT_SUPPORTED
        assert result.project is loaded_project


class TestProjectExtractorSuccess:
    """Tests for successful extraction scenarios."""

    def test_extract_successful_extraction(
        self, extractor, plugin_manager, loaded_project
    ):
        """Test extraction when plugin succeeds."""
        entry = ExtractionEntry(
            entry_id="test:id",
            entry_type=ExtractionEntryType.TEXT,
            text="Test text",
            source_path=Path("file.txt"),
        )
        mock_plugin = Mock()
        mock_plugin.extract_data.return_value = ExtractionResult(
            status=ExtractionStatus.EXTRACTED,
            entries=(entry,),
        )
        plugin_manager.get.return_value = mock_plugin

        result = extractor.extract(loaded_project)
        assert result.status == ExtractionStatus.EXTRACTED
        assert len(result.entries) == 1
        assert result.entries[0] == entry
        assert result.project is loaded_project

    def test_extract_partial_extraction(
        self, extractor, plugin_manager, loaded_project
    ):
        """Test extraction when plugin returns PARTIAL."""
        mock_plugin = Mock()
        mock_plugin.extract_data.return_value = ExtractionResult(
            status=ExtractionStatus.PARTIAL,
            entries=(),
            warnings=(
                ExtractionIssue(
                    severity=ExtractionIssueSeverity.WARNING,
                    code="partial_code",
                    message="Partial extraction",
                ),
            ),
        )
        plugin_manager.get.return_value = mock_plugin

        result = extractor.extract(loaded_project)
        assert result.status == ExtractionStatus.PARTIAL
        assert len(result.warnings) == 1


class TestProjectExtractorPluginException:
    """Tests for plugin exception handling."""

    def test_extract_plugin_raises_exception(
        self, extractor, plugin_manager, loaded_project, caplog
    ):
        """Test extraction when plugin raises an unexpected exception."""
        mock_plugin = Mock()
        mock_plugin.extract_data.side_effect = RuntimeError("Unexpected error")
        plugin_manager.get.return_value = mock_plugin

        result = extractor.extract(loaded_project)
        assert result.status == ExtractionStatus.FAILED
        assert len(result.errors) == 1
        assert result.errors[0].code == "extraction_failed"
        assert "Unexpected error" in result.errors[0].message
        # Verify exception was logged
        assert "Unexpected error during extraction" in caplog.text


class TestProjectExtractorProjectReference:
    """Tests for project reference attachment."""

    def test_extractor_attaches_project_to_result(
        self, extractor, plugin_manager, loaded_project
    ):
        """Test that extractor attaches project to result."""
        mock_plugin = Mock()
        # Plugin returns result without project
        mock_plugin.extract_data.return_value = ExtractionResult(
            status=ExtractionStatus.EXTRACTED,
            entries=(),
            project=None,
        )
        plugin_manager.get.return_value = mock_plugin

        result = extractor.extract(loaded_project)
        assert result.project is loaded_project

    def test_extractor_preserves_existing_project_reference(
        self, extractor, plugin_manager, loaded_project
    ):
        """Test that extractor preserves existing project reference."""
        other_project = Project(
            path=loaded_project.path / "other",
            status=ProjectLoadStatus.LOADED,
        )
        mock_plugin = Mock()
        # Plugin returns result with its own project reference
        mock_plugin.extract_data.return_value = ExtractionResult(
            status=ExtractionStatus.EXTRACTED,
            entries=(),
            project=other_project,
        )
        plugin_manager.get.return_value = mock_plugin

        result = extractor.extract(loaded_project)
        # Should preserve the plugin's project reference
        assert result.project is other_project
