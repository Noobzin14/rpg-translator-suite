"""Tests for the Plugin Structure API (Sprint 0.3, Stage 2)."""

from pathlib import Path

import pytest

from app.core.base_plugin import BasePlugin
from app.core.detection import DetectionResult, DetectionStatus
from app.core.project_model import (
    ProjectFileKind,
    ProjectFileRole,
    ProjectFileSpec,
    ProjectStructureSpec,
)


class TestProjectFileSpec:
    """Tests for ProjectFileSpec dataclass."""

    def test_create_project_file_spec_minimal(self) -> None:
        """Can create a ProjectFileSpec with minimal required fields."""
        spec = ProjectFileSpec(
            relative_path=Path("file.txt"),
            kind=ProjectFileKind.FILE,
            role=ProjectFileRole.UNKNOWN,
        )
        assert spec.relative_path == Path("file.txt")
        assert spec.kind == ProjectFileKind.FILE
        assert spec.role == ProjectFileRole.UNKNOWN
        assert spec.required is False
        assert spec.description is None

    def test_create_project_file_spec_with_all_fields(self) -> None:
        """Can create a ProjectFileSpec with all fields."""
        spec = ProjectFileSpec(
            relative_path=Path("config.json"),
            kind=ProjectFileKind.FILE,
            role=ProjectFileRole.CONFIG,
            required=True,
            description="Configuration file",
        )
        assert spec.relative_path == Path("config.json")
        assert spec.kind == ProjectFileKind.FILE
        assert spec.role == ProjectFileRole.CONFIG
        assert spec.required is True
        assert spec.description == "Configuration file"

    def test_project_file_spec_is_frozen(self) -> None:
        """ProjectFileSpec is immutable (frozen dataclass)."""
        spec = ProjectFileSpec(
            relative_path=Path("test"),
            kind=ProjectFileKind.FILE,
            role=ProjectFileRole.UNKNOWN,
        )
        with pytest.raises(AttributeError):
            spec.required = True  # type: ignore[misc]


class TestProjectStructureSpec:
    """Tests for ProjectStructureSpec dataclass."""

    def test_create_project_structure_spec_empty_defaults(self) -> None:
        """Can create a ProjectStructureSpec with empty defaults."""
        spec = ProjectStructureSpec()
        assert spec.metadata == {}
        assert spec.expected_files == ()
        assert spec.expected_directories == ()
        assert spec.relevant_files == ()
        assert spec.relevant_directories == ()

    def test_create_project_structure_spec_with_values(self) -> None:
        """Can create a ProjectStructureSpec with values."""
        file_spec = ProjectFileSpec(
            relative_path=Path("file.txt"),
            kind=ProjectFileKind.FILE,
            role=ProjectFileRole.UNKNOWN,
        )
        dir_spec = ProjectFileSpec(
            relative_path=Path("data"),
            kind=ProjectFileKind.DIRECTORY,
            role=ProjectFileRole.DATA,
        )
        spec = ProjectStructureSpec(
            metadata={"engine": "test", "version": 1},
            expected_files=(file_spec,),
            expected_directories=(dir_spec,),
            relevant_files=(file_spec,),
            relevant_directories=(dir_spec,),
        )
        assert spec.metadata["engine"] == "test"
        assert len(spec.expected_files) == 1
        assert len(spec.expected_directories) == 1
        assert len(spec.relevant_files) == 1
        assert len(spec.relevant_directories) == 1

    def test_project_structure_spec_is_frozen(self) -> None:
        """ProjectStructureSpec is immutable (frozen dataclass)."""
        spec = ProjectStructureSpec()
        with pytest.raises(AttributeError):
            spec.metadata = {"key": "value"}  # type: ignore[misc]


class DummyPlugin(BasePlugin):
    """A dummy plugin for testing that does not override describe_project_structure."""

    plugin_id = "dummy"
    display_name = "Dummy Plugin"

    def detect(self, project_path: Path) -> bool:
        """Always returns False for testing."""
        return False


class TestBasePluginDescribeProjectStructure:
    """Tests for BasePlugin.describe_project_structure()."""

    def test_base_plugin_returns_empty_spec(self) -> None:
        """BasePlugin provides a safe default implementation returning empty spec."""
        plugin = DummyPlugin()
        project_path = Path("/test/project")
        detection = DetectionResult(
            status=DetectionStatus.UNKNOWN,
            project_path=project_path,
            reason="Test detection",
        )
        result = plugin.describe_project_structure(project_path, detection)
        assert isinstance(result, ProjectStructureSpec)
        assert result.metadata == {}
        assert result.expected_files == ()
        assert result.expected_directories == ()
        assert result.relevant_files == ()
        assert result.relevant_directories == ()

    def test_base_plugin_does_not_raise(self) -> None:
        """BasePlugin.default implementation does not raise NotImplementedError."""
        plugin = DummyPlugin()
        project_path = Path("/test/project")
        detection = DetectionResult(
            status=DetectionStatus.UNKNOWN,
            project_path=project_path,
            reason="Test detection",
        )
        # Should not raise any exception
        result = plugin.describe_project_structure(project_path, detection)
        assert result is not None


class TestRPGMakerMVPluginDescribeProjectStructure:
    """Tests for RPG Maker MV plugin's describe_project_structure()."""

    @pytest.fixture
    def mv_plugin(self):
        """Create an instance of the RPG Maker MV plugin."""
        from plugins.rpgmaker_mv.plugin import RPGMakerMVPlugin

        return RPGMakerMVPlugin()

    def test_mv_plugin_returns_project_structure_spec(self, mv_plugin) -> None:
        """MV plugin returns a ProjectStructureSpec."""
        project_path = Path("/test/mv_project")
        detection = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=project_path,
            engine="rpgmaker_mv",
            display_name="RPG Maker MV",
        )
        result = mv_plugin.describe_project_structure(project_path, detection)
        assert isinstance(result, ProjectStructureSpec)

    def test_mv_structure_contains_expected_files(self, mv_plugin) -> None:
        """MV structure contains expected file paths."""
        project_path = Path("/test/mv_project")
        detection = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=project_path,
            engine="rpgmaker_mv",
        )
        result = mv_plugin.describe_project_structure(project_path, detection)

        # Check expected files exist
        assert len(result.expected_files) >= 2

        # Find package.json spec
        package_json_spec = next(
            (f for f in result.expected_files if f.relative_path == Path("package.json")),
            None,
        )
        assert package_json_spec is not None
        assert package_json_spec.kind == ProjectFileKind.FILE
        assert package_json_spec.required is True

        # Find System.json spec
        system_json_spec = next(
            (f for f in result.expected_files if f.relative_path == Path("www/data/System.json")),
            None,
        )
        assert system_json_spec is not None
        assert system_json_spec.kind == ProjectFileKind.FILE
        assert system_json_spec.required is True

    def test_mv_structure_contains_expected_directories(self, mv_plugin) -> None:
        """MV structure contains expected directory paths."""
        project_path = Path("/test/mv_project")
        detection = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=project_path,
            engine="rpgmaker_mv",
        )
        result = mv_plugin.describe_project_structure(project_path, detection)

        # Check expected directories exist
        assert len(result.expected_directories) >= 3

        # Find www directory spec
        www_dir_spec = next(
            (d for d in result.expected_directories if d.relative_path == Path("www")),
            None,
        )
        assert www_dir_spec is not None
        assert www_dir_spec.kind == ProjectFileKind.DIRECTORY
        assert www_dir_spec.required is True

        # Find www/data directory spec
        www_data_dir_spec = next(
            (d for d in result.expected_directories if d.relative_path == Path("www/data")),
            None,
        )
        assert www_data_dir_spec is not None
        assert www_data_dir_spec.kind == ProjectFileKind.DIRECTORY
        assert www_data_dir_spec.required is True

        # Find www/js directory spec
        www_js_dir_spec = next(
            (d for d in result.expected_directories if d.relative_path == Path("www/js")),
            None,
        )
        assert www_js_dir_spec is not None
        assert www_js_dir_spec.kind == ProjectFileKind.DIRECTORY
        assert www_js_dir_spec.required is True

    def test_mv_structure_contains_relevant_files(self, mv_plugin) -> None:
        """MV structure contains relevant file paths."""
        project_path = Path("/test/mv_project")
        detection = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=project_path,
            engine="rpgmaker_mv",
        )
        result = mv_plugin.describe_project_structure(project_path, detection)

        # Find rpg_core.js spec in relevant files
        rpg_core_spec = next(
            (f for f in result.relevant_files if f.relative_path == Path("www/js/rpg_core.js")),
            None,
        )
        assert rpg_core_spec is not None
        assert rpg_core_spec.kind == ProjectFileKind.FILE
        assert rpg_core_spec.role == ProjectFileRole.SCRIPT
        assert rpg_core_spec.required is False

    def test_mv_paths_are_relative(self, mv_plugin) -> None:
        """MV plugin uses relative paths, not absolute paths."""
        project_path = Path("/test/mv_project")
        detection = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=project_path,
            engine="rpgmaker_mv",
        )
        result = mv_plugin.describe_project_structure(project_path, detection)

        # All paths should be relative (not absolute)
        for file_spec in result.expected_files + result.relevant_files:
            assert not file_spec.relative_path.is_absolute(), (
                f"Path {file_spec.relative_path} should be relative"
            )

        for dir_spec in result.expected_directories + result.relevant_directories:
            assert not dir_spec.relative_path.is_absolute(), (
                f"Path {dir_spec.relative_path} should be relative"
            )

    def test_mv_uses_generic_core_kinds_and_roles(self, mv_plugin) -> None:
        """MV plugin uses generic kinds and roles from Core, not MV-specific ones."""
        project_path = Path("/test/mv_project")
        detection = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=project_path,
            engine="rpgmaker_mv",
        )
        result = mv_plugin.describe_project_structure(project_path, detection)

        # All kinds should be from ProjectFileKind enum
        all_specs = (
            result.expected_files
            + result.expected_directories
            + result.relevant_files
            + result.relevant_directories
        )
        for spec in all_specs:
            assert isinstance(spec.kind, ProjectFileKind)
            assert isinstance(spec.role, ProjectFileRole)

    def test_describe_project_structure_receives_correct_args(self, mv_plugin) -> None:
        """Method correctly receives Path and DetectionResult arguments."""
        project_path = Path("/test/mv_project")
        detection = DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=project_path,
            engine="rpgmaker_mv",
            display_name="RPG Maker MV",
            version="1.6.1",
        )
        # Should accept these arguments without error
        result = mv_plugin.describe_project_structure(project_path, detection)
        assert isinstance(result, ProjectStructureSpec)


class TestCoreDoesNotContainMVSpecificPaths:
    """Tests to ensure Core remains engine-independent."""

    def test_no_mv_specific_strings_in_core_project_model(self) -> None:
        """Core project_model.py does not contain MV-specific strings."""
        import app.core.project_model as pm

        source_file = pm.__file__
        assert source_file is not None

        content = Path(source_file).read_text(encoding="utf-8")

        # These MV-specific strings should NOT appear in core
        mv_specific_strings = [
            "rpg_core",
            "System.json",
            "package.json",
            "www/data",
            "www/js",
            "RPG Maker",
            "rpgmaker",
        ]

        for mv_string in mv_specific_strings:
            assert mv_string not in content, (
                f"Core project_model.py should not contain MV-specific string: {mv_string}"
            )

    def test_no_mv_specific_strings_in_core_base_plugin(self) -> None:
        """Core base_plugin.py does not contain MV-specific strings."""
        import app.core.base_plugin as bp

        source_file = bp.__file__
        assert source_file is not None

        content = Path(source_file).read_text(encoding="utf-8")

        mv_specific_strings = [
            "rpg_core",
            "System.json",
            "www/data",
            "www/js",
            "RPG Maker",
        ]

        for mv_string in mv_specific_strings:
            assert mv_string not in content, (
                f"Core base_plugin.py should not contain MV-specific string: {mv_string}"
            )
