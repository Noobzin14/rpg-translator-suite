"""Tests for the ProjectLoader (Sprint 0.3, Stage 3)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock

import pytest

from app.core.base_plugin import BasePlugin
from app.core.detection import (
    ConfidenceLevel,
    DetectionEvidence,
    DetectionResult,
    DetectionStatus,
)
from app.core.plugin_manager import PluginManager
from app.core.plugin_registry import PluginRegistry
from app.core.project_detector import ProjectDetector
from app.core.project_loader import ProjectLoader
from app.core.project_model import (
    ProjectFileKind,
    ProjectFileRole,
    ProjectFileSpec,
    ProjectIssueSeverity,
    ProjectLoadResult,
    ProjectLoadStatus,
    ProjectStructureSpec,
)


class FakePlugin(BasePlugin):
    """A fake plugin for testing."""

    plugin_id: ClassVar[str] = "fake_plugin"
    display_name: ClassVar[str] = "Fake Plugin"

    def detect(self, project_path: Path) -> bool:
        """Return whether this plugin supports the path."""
        return False


class TestProjectLoaderInitialization:
    """Tests for ProjectLoader initialization."""

    def test_create_project_loader(self, tmp_path: Path) -> None:
        """Can create a ProjectLoader with detector and plugin_manager."""
        registry = PluginRegistry()
        plugin_manager = PluginManager(
            plugin_directory=tmp_path / "plugins",
            registry=registry,
        )
        detector = ProjectDetector(plugin_loader=MagicMock())
        loader = ProjectLoader(detector=detector, plugin_manager=plugin_manager)

        assert loader is not None
        assert loader._detector is detector
        assert loader._plugin_manager is plugin_manager


class TestProjectLoaderInvalidPath:
    """Tests for invalid path handling."""

    @pytest.fixture
    def loader_setup(self, tmp_path: Path) -> tuple[ProjectLoader, Path]:
        """Create a loader setup for testing."""
        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )
        detector = ProjectDetector(plugin_loader=MagicMock())
        loader = ProjectLoader(detector=detector, plugin_manager=plugin_manager)
        return loader, tmp_path

    def test_nonexistent_path_returns_invalid_path(
        self,
        loader_setup: tuple[ProjectLoader, Path],
    ) -> None:
        """Nonexistent path returns INVALID_PATH status."""
        loader, _ = loader_setup
        nonexistent_path = Path("/nonexistent/path/12345")

        result = loader.load(nonexistent_path)

        assert result.status == ProjectLoadStatus.INVALID_PATH
        assert result.project is None
        assert len(result.errors) == 1
        assert result.errors[0].code == "invalid_path"
        assert result.detection is None

    def test_file_instead_of_directory_returns_invalid_path(
        self,
        loader_setup: tuple[ProjectLoader, Path],
    ) -> None:
        """Path pointing to a file returns INVALID_PATH status."""
        loader, tmp_path = loader_setup
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("test content")

        result = loader.load(file_path)

        assert result.status == ProjectLoadStatus.INVALID_PATH
        assert result.project is None
        assert len(result.errors) == 1
        assert result.errors[0].code == "invalid_path"
        assert result.detection is None


class TestProjectLoaderUnknownEngine:
    """Tests for unknown engine handling."""

    def test_unknown_detection_returns_unknown_engine(
        self,
        tmp_path: Path,
    ) -> None:
        """UNKNOWN detection status returns UNKNOWN_ENGINE."""
        # Create mock detector that returns UNKNOWN
        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = DetectionResult(
            status=DetectionStatus.UNKNOWN,
            project_path=tmp_path,
            reason="No supported engine detected.",
        )

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        assert result.status == ProjectLoadStatus.UNKNOWN_ENGINE
        assert result.project is None
        assert len(result.errors) == 1
        assert result.errors[0].code == "unknown_engine"
        assert result.detection is not None
        assert result.detection.status == DetectionStatus.UNKNOWN


class TestProjectLoaderConflict:
    """Tests for engine conflict handling."""

    def test_conflict_detection_returns_engine_conflict(
        self,
        tmp_path: Path,
    ) -> None:
        """CONFLICT detection status returns ENGINE_CONFLICT."""
        # Create mock detector that returns CONFLICT
        conflict_result1 = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="engine_a",
            display_name="Engine A",
        )
        conflict_result2 = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="engine_b",
            display_name="Engine B",
        )

        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = DetectionResult(
            status=DetectionStatus.CONFLICT,
            project_path=tmp_path,
            reason="Multiple engine detectors matched.",
            conflicts=(conflict_result1, conflict_result2),
        )

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        assert result.status == ProjectLoadStatus.ENGINE_CONFLICT
        assert result.project is None
        assert len(result.errors) == 1
        assert result.errors[0].code == "engine_conflict"
        assert result.detection is not None
        assert result.detection.status == DetectionStatus.CONFLICT
        assert len(result.detection.conflicts) == 2


class TestProjectLoaderIncomplete:
    """Tests for incomplete detection handling."""

    def test_incomplete_without_engine_returns_incomplete(
        self,
        tmp_path: Path,
    ) -> None:
        """INCOMPLETE detection without engine returns INCOMPLETE."""
        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = DetectionResult(
            status=DetectionStatus.INCOMPLETE,
            project_path=tmp_path,
            engine=None,
            reason="Partial evidence found but not confirmed.",
        )

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        assert result.status == ProjectLoadStatus.INCOMPLETE
        assert result.project is None
        assert result.detection is not None
        assert result.detection.status == DetectionStatus.INCOMPLETE

    def test_incomplete_with_engine_returns_incomplete(
        self,
        tmp_path: Path,
    ) -> None:
        """INCOMPLETE detection with engine returns INCOMPLETE without project."""
        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = DetectionResult(
            status=DetectionStatus.INCOMPLETE,
            project_path=tmp_path,
            engine="rpgmaker_mv",
            display_name="RPG Maker MV",
            reason="Partial evidence found.",
        )

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        assert result.status == ProjectLoadStatus.INCOMPLETE
        assert result.project is None
        assert result.detection is not None
        assert result.detection.engine == "rpgmaker_mv"


class TestProjectLoaderDetectedAndLoaded:
    """Tests for successful detection and loading."""

    def test_mv_detected_and_structure_loaded(
        self,
        tmp_path: Path,
    ) -> None:
        """DETECTED status with valid structure returns LOADED."""
        # Create a fake MV-like project structure
        www_dir = tmp_path / "www"
        www_data_dir = www_dir / "data"
        www_js_dir = www_dir / "js"
        www_data_dir.mkdir(parents=True)
        www_js_dir.mkdir(parents=True)

        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test", "rpg_core": true}')

        system_json = www_data_dir / "System.json"
        system_json.write_text('{"title": "Test Game"}')

        rpg_core_js = www_js_dir / "rpg_core.js"
        rpg_core_js.write_text("// RPG Maker MV v1.6.1")

        # Create fake plugin
        class FakeMVPlugin(BasePlugin):
            plugin_id = "rpgmaker_mv"
            display_name = "RPG Maker MV"

            def detect(self, project_path: Path) -> bool:
                return True

            def describe_project_structure(
                self,
                project_path: Path,
                detection: DetectionResult,
            ) -> ProjectStructureSpec:
                return ProjectStructureSpec(
                    metadata={"engine": "rpgmaker_mv"},
                    expected_files=(
                        ProjectFileSpec(
                            relative_path=Path("package.json"),
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.CONFIG,
                            required=True,
                        ),
                        ProjectFileSpec(
                            relative_path=Path("www/data/System.json"),
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.DATA,
                            required=True,
                        ),
                    ),
                    expected_directories=(
                        ProjectFileSpec(
                            relative_path=Path("www"),
                            kind=ProjectFileKind.DIRECTORY,
                            role=ProjectFileRole.DATA,
                            required=True,
                        ),
                        ProjectFileSpec(
                            relative_path=Path("www/data"),
                            kind=ProjectFileKind.DIRECTORY,
                            role=ProjectFileRole.DATA,
                            required=True,
                        ),
                        ProjectFileSpec(
                            relative_path=Path("www/js"),
                            kind=ProjectFileKind.DIRECTORY,
                            role=ProjectFileRole.SCRIPT,
                            required=True,
                        ),
                    ),
                    relevant_files=(
                        ProjectFileSpec(
                            relative_path=Path("www/js/rpg_core.js"),
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.SCRIPT,
                            required=False,
                        ),
                    ),
                )

        # Setup detector and plugin manager
        detection_result = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="rpgmaker_mv",
            display_name="RPG Maker MV",
            version="1.6.1",
            confidence=ConfidenceLevel.HIGH,
        )

        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = detection_result

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )
        plugin_manager.register(FakeMVPlugin())

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        assert result.status == ProjectLoadStatus.LOADED
        assert result.project is not None
        assert result.project.engine == "rpgmaker_mv"
        assert result.project.engine_display_name == "RPG Maker MV"
        assert result.project.engine_version == "1.6.1"
        assert result.detection == detection_result
        assert result.project.structure is not None
        assert len(result.project.files) > 0


class TestProjectLoaderPluginNotFound:
    """Tests for plugin not found scenario."""

    def test_detected_but_plugin_not_available(
        self,
        tmp_path: Path,
    ) -> None:
        """DETECTED with unavailable plugin returns READ_ERROR."""
        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="nonexistent_engine",
            display_name="Nonexistent Engine",
        )

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        assert result.status == ProjectLoadStatus.READ_ERROR
        assert result.project is None
        assert len(result.errors) == 1
        assert result.errors[0].code == "plugin_not_available"
        assert result.detection is not None


class TestProjectLoaderMissingFiles:
    """Tests for missing expected files/directories."""

    def test_missing_required_file_returns_incomplete(
        self,
        tmp_path: Path,
    ) -> None:
        """Missing required file results in INCOMPLETE status."""
        # Create partial structure (missing System.json)
        www_dir = tmp_path / "www"
        www_dir.mkdir()

        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test"}')

        class FakePlugin(BasePlugin):
            plugin_id = "test_engine"
            display_name = "Test Engine"

            def detect(self, project_path: Path) -> bool:
                return True

            def describe_project_structure(
                self,
                project_path: Path,
                detection: DetectionResult,
            ) -> ProjectStructureSpec:
                return ProjectStructureSpec(
                    expected_files=(
                        ProjectFileSpec(
                            relative_path=Path("package.json"),
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.CONFIG,
                            required=True,
                        ),
                        ProjectFileSpec(
                            relative_path=Path("www/data/System.json"),
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.DATA,
                            required=True,
                        ),
                    ),
                )

        detection_result = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="test_engine",
        )

        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = detection_result

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )
        plugin_manager.register(FakePlugin())

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        assert result.status == ProjectLoadStatus.INCOMPLETE
        assert result.project is not None
        assert any(i.code == "missing_expected_file" for i in result.errors)


class TestProjectLoaderOptionalFiles:
    """Tests for optional files handling."""

    def test_missing_optional_file_creates_warning(
        self,
        tmp_path: Path,
    ) -> None:
        """Missing optional file creates warning, not error."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test"}')

        class FakePlugin(BasePlugin):
            plugin_id = "test_engine"
            display_name = "Test Engine"

            def detect(self, project_path: Path) -> bool:
                return True

            def describe_project_structure(
                self,
                project_path: Path,
                detection: DetectionResult,
            ) -> ProjectStructureSpec:
                return ProjectStructureSpec(
                    expected_files=(
                        ProjectFileSpec(
                            relative_path=Path("package.json"),
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.CONFIG,
                            required=True,
                        ),
                    ),
                    relevant_files=(
                        ProjectFileSpec(
                            relative_path=Path("optional.txt"),
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.UNKNOWN,
                            required=False,
                        ),
                    ),
                )

        detection_result = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="test_engine",
        )

        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = detection_result

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )
        plugin_manager.register(FakePlugin())

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        # Should still be LOADED since only optional file is missing
        assert result.status == ProjectLoadStatus.LOADED
        assert result.project is not None
        # Check for warning about missing optional file
        assert any(
            i.code == "missing_expected_file" and i.severity == ProjectIssueSeverity.WARNING
            for i in result.project.issues
        )


class TestProjectLoaderMetadata:
    """Tests for metadata handling."""

    def test_metadata_from_spec_reaches_project(
        self,
        tmp_path: Path,
    ) -> None:
        """Metadata from ProjectStructureSpec reaches Project.metadata."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test"}')

        class FakePlugin(BasePlugin):
            plugin_id = "test_engine"
            display_name = "Test Engine"

            def detect(self, project_path: Path) -> bool:
                return True

            def describe_project_structure(
                self,
                project_path: Path,
                detection: DetectionResult,
            ) -> ProjectStructureSpec:
                return ProjectStructureSpec(
                    metadata={
                        "engine_name": "test_engine",
                        "version": 1,
                        "active": True,
                    },
                    expected_files=(
                        ProjectFileSpec(
                            relative_path=Path("package.json"),
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.CONFIG,
                            required=True,
                        ),
                    ),
                )

        detection_result = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="test_engine",
        )

        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = detection_result

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )
        plugin_manager.register(FakePlugin())

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        assert result.project is not None
        assert result.project.metadata["engine_name"] == "test_engine"
        assert result.project.metadata["version"] == 1
        assert result.project.metadata["active"] is True


class TestProjectLoaderPathSecurity:
    """Tests for path security validation."""

    def test_absolute_path_in_spec_rejected(
        self,
        tmp_path: Path,
    ) -> None:
        """Absolute paths in ProjectFileSpec are rejected."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test"}')

        class FakePlugin(BasePlugin):
            plugin_id = "test_engine"
            display_name = "Test Engine"

            def detect(self, project_path: Path) -> bool:
                return True

            def describe_project_structure(
                self,
                project_path: Path,
                detection: DetectionResult,
            ) -> ProjectStructureSpec:
                return ProjectStructureSpec(
                    expected_files=(
                        ProjectFileSpec(
                            relative_path=Path("/etc/passwd"),  # Absolute path!
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.CONFIG,
                            required=True,
                        ),
                    ),
                )

        detection_result = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="test_engine",
        )

        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = detection_result

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )
        plugin_manager.register(FakePlugin())

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        # Should have an issue about invalid relative path
        assert any(i.code == "invalid_relative_path" for i in result.errors or result.warnings)

    def test_path_traversal_in_spec_rejected(
        self,
        tmp_path: Path,
    ) -> None:
        """Path traversal attempts in ProjectFileSpec are rejected."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test"}')

        # Create a file outside the project
        outside_file = tmp_path.parent / "outside.txt"
        outside_file.write_text("secret data")

        class FakePlugin(BasePlugin):
            plugin_id = "test_engine"
            display_name = "Test Engine"

            def detect(self, project_path: Path) -> bool:
                return True

            def describe_project_structure(
                self,
                project_path: Path,
                detection: DetectionResult,
            ) -> ProjectStructureSpec:
                return ProjectStructureSpec(
                    expected_files=(
                        ProjectFileSpec(
                            relative_path=Path("../../outside.txt"),  # Path traversal!
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.UNKNOWN,
                            required=True,
                        ),
                    ),
                )

        detection_result = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="test_engine",
        )

        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = detection_result

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )
        plugin_manager.register(FakePlugin())

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        # Should have an issue about invalid relative path
        assert any(i.code == "invalid_relative_path" for i in result.errors or result.warnings)


class TestProjectLoaderSymlinks:
    """Tests for symlink handling."""

    def test_symlink_outside_project_handled(
        self,
        tmp_path: Path,
    ) -> None:
        """Symlinks pointing outside project are handled safely."""
        # Skip if symlinks are not supported
        if os.name == "nt":
            pytest.skip("Symlinks not well supported on Windows in test environment")

        # Create project structure
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test"}')

        # Create file outside project
        outside_file = tmp_path.parent / "outside.txt"
        outside_file.write_text("outside content")

        # Create symlink inside project pointing outside
        symlink_path = tmp_path / "link_to_outside.txt"
        try:
            symlink_path.symlink_to(outside_file)
        except OSError:
            pytest.skip("Cannot create symlinks in this environment")

        class FakePlugin(BasePlugin):
            plugin_id = "test_engine"
            display_name = "Test Engine"

            def detect(self, project_path: Path) -> bool:
                return True

            def describe_project_structure(
                self,
                project_path: Path,
                detection: DetectionResult,
            ) -> ProjectStructureSpec:
                return ProjectStructureSpec(
                    expected_files=(
                        ProjectFileSpec(
                            relative_path=Path("package.json"),
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.CONFIG,
                            required=True,
                        ),
                        ProjectFileSpec(
                            relative_path=Path("link_to_outside.txt"),
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.UNKNOWN,
                            required=False,
                        ),
                    ),
                )

        detection_result = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="test_engine",
        )

        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = detection_result

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )
        plugin_manager.register(FakePlugin())

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        # Should have a warning about symlink
        assert any(
            "symlink" in i.code.lower()
            for i in result.warnings + result.errors + result.project.issues  # type: ignore
        )


class TestProjectLoaderDeduplication:
    """Tests for deduplication of files between expected and relevant."""

    def test_no_duplicate_projectfiles(
        self,
        tmp_path: Path,
    ) -> None:
        """Same path in expected_files and relevant_files doesn't create duplicates."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test"}')

        class FakePlugin(BasePlugin):
            plugin_id = "test_engine"
            display_name = "Test Engine"

            def detect(self, project_path: Path) -> bool:
                return True

            def describe_project_structure(
                self,
                project_path: Path,
                detection: DetectionResult,
            ) -> ProjectStructureSpec:
                # Same file in both expected and relevant
                spec = ProjectFileSpec(
                    relative_path=Path("package.json"),
                    kind=ProjectFileKind.FILE,
                    role=ProjectFileRole.CONFIG,
                    required=True,
                )
                return ProjectStructureSpec(
                    expected_files=(spec,),
                    relevant_files=(spec,),  # Duplicate!
                )

        detection_result = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="test_engine",
        )

        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = detection_result

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )
        plugin_manager.register(FakePlugin())

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        assert result.project is not None
        # Count how many ProjectFiles have relative_path == package.json
        package_files = [
            f for f in result.project.files if f.relative_path == Path("package.json")
        ]
        # Should only have one, not two
        assert len(package_files) == 1
        # Required should be preserved
        assert package_files[0].is_required is True


class TestProjectLoaderDetectionPreservation:
    """Tests for DetectionResult preservation."""

    def test_detection_result_preserved_in_load_result(
        self,
        tmp_path: Path,
    ) -> None:
        """DetectionResult is preserved in ProjectLoadResult."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test"}')

        class FakePlugin(BasePlugin):
            plugin_id = "test_engine"
            display_name = "Test Engine"

            def detect(self, project_path: Path) -> bool:
                return True

            def describe_project_structure(
                self,
                project_path: Path,
                detection: DetectionResult,
            ) -> ProjectStructureSpec:
                return ProjectStructureSpec(
                    expected_files=(
                        ProjectFileSpec(
                            relative_path=Path("package.json"),
                            kind=ProjectFileKind.FILE,
                            role=ProjectFileRole.CONFIG,
                            required=True,
                        ),
                    ),
                )

        original_detection = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=tmp_path,
            engine="test_engine",
            display_name="Test Engine",
            version="1.0.0",
            confidence=ConfidenceLevel.HIGH,
            evidence=(
                DetectionEvidence(
                    path=package_json,
                    description="Test evidence",
                    confidence_weight=1,
                ),
            ),
            reason="Test detection",
        )

        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = original_detection

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )
        plugin_manager.register(FakePlugin())

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        assert result.detection is not None
        assert result.detection.status == original_detection.status
        assert result.detection.engine == original_detection.engine
        assert result.detection.display_name == original_detection.display_name
        assert result.detection.version == original_detection.version
        assert result.detection.confidence == original_detection.confidence
        assert len(result.detection.evidence) == len(original_detection.evidence)


class TestProjectLoaderEngineIndependent:
    """Tests to ensure ProjectLoader remains engine-independent."""

    def test_no_mv_specific_strings_in_project_loader(self) -> None:
        """project_loader.py does not contain MV-specific strings."""
        import app.core.project_loader as pl

        source_file = pl.__file__
        assert source_file is not None

        content = Path(source_file).read_text(encoding="utf-8")

        # These MV-specific strings should NOT appear in core
        mv_specific_strings = [
            "rpg_core",
            "System.json",
            "www/data",
            "www/js",
            "RPG Maker MV",
        ]

        for mv_string in mv_specific_strings:
            assert mv_string not in content, (
                f"ProjectLoader should not contain MV-specific string: {mv_string}"
            )

    def test_project_loader_uses_abstractions(self) -> None:
        """ProjectLoader depends on abstractions, not concrete implementations."""
        from app.core.project_loader import ProjectLoader

        # Check that ProjectLoader uses abstract types
        import inspect

        source = inspect.getsource(ProjectLoader)

        # Should use DetectionResult, not specific result types
        assert "DetectionResult" in source
        # Should use ProjectStructureSpec, not engine-specific specs
        assert "ProjectStructureSpec" in source
        # Should use PluginManager API
        assert "plugin_manager" in source.lower()


class TestProjectLoadResult:
    """Tests for ProjectLoadResult structure."""

    def test_load_result_contains_all_fields(
        self,
        tmp_path: Path,
    ) -> None:
        """ProjectLoadResult contains status, project, warnings, errors, detection."""
        mock_detector = MagicMock(spec=ProjectDetector)
        mock_detector.detect.return_value = DetectionResult(
            status=DetectionStatus.UNKNOWN,
            project_path=tmp_path,
        )

        registry = PluginRegistry()
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_manager = PluginManager(
            plugin_directory=plugin_dir,
            registry=registry,
        )

        loader = ProjectLoader(detector=mock_detector, plugin_manager=plugin_manager)
        result = loader.load(tmp_path)

        assert hasattr(result, "status")
        assert hasattr(result, "project")
        assert hasattr(result, "warnings")
        assert hasattr(result, "errors")
        assert hasattr(result, "detection")
        assert isinstance(result.warnings, tuple)
        assert isinstance(result.errors, tuple)
