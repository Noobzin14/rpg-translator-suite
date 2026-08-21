"""Tests for the engine-independent project models."""

from pathlib import Path

import pytest

from app.core.project_model import (
    Project,
    ProjectFile,
    ProjectFileKind,
    ProjectFileRole,
    ProjectIssue,
    ProjectIssueSeverity,
    ProjectLoadResult,
    ProjectLoadStatus,
    ProjectMetadata,
    ProjectStructure,
)


class TestProjectLoadStatus:
    """Tests for ProjectLoadStatus enum."""

    def test_all_status_values_exist(self) -> None:
        """All required status values are defined."""
        assert ProjectLoadStatus.LOADED.value == "loaded"
        assert ProjectLoadStatus.INCOMPLETE.value == "incomplete"
        assert ProjectLoadStatus.NOT_LOADED.value == "not_loaded"
        assert ProjectLoadStatus.INVALID_PATH.value == "invalid_path"
        assert ProjectLoadStatus.UNKNOWN_ENGINE.value == "unknown_engine"
        assert ProjectLoadStatus.ENGINE_CONFLICT.value == "engine_conflict"
        assert ProjectLoadStatus.ACCESS_ERROR.value == "access_error"
        assert ProjectLoadStatus.READ_ERROR.value == "read_error"

    def test_status_is_string_enum(self) -> None:
        """ProjectLoadStatus is a string-based enum."""
        assert isinstance(ProjectLoadStatus.LOADED, str)
        assert ProjectLoadStatus.LOADED == "loaded"


class TestProjectIssueSeverity:
    """Tests for ProjectIssueSeverity enum."""

    def test_all_severity_values_exist(self) -> None:
        """All required severity values are defined."""
        assert ProjectIssueSeverity.INFO.value == "info"
        assert ProjectIssueSeverity.WARNING.value == "warning"
        assert ProjectIssueSeverity.ERROR.value == "error"

    def test_severity_is_string_enum(self) -> None:
        """ProjectIssueSeverity is a string-based enum."""
        assert isinstance(ProjectIssueSeverity.INFO, str)
        assert ProjectIssueSeverity.INFO == "info"


class TestProjectIssue:
    """Tests for ProjectIssue dataclass."""

    def test_create_project_issue_minimal(self) -> None:
        """Can create a ProjectIssue with minimal fields."""
        issue = ProjectIssue(
            severity=ProjectIssueSeverity.WARNING,
            code="W001",
            message="Test warning message",
        )
        assert issue.severity == ProjectIssueSeverity.WARNING
        assert issue.code == "W001"
        assert issue.message == "Test warning message"
        assert issue.path is None

    def test_create_project_issue_with_path(self) -> None:
        """Can create a ProjectIssue with an optional path."""
        test_path = Path("/some/path/file.txt")
        issue = ProjectIssue(
            severity=ProjectIssueSeverity.ERROR,
            code="E001",
            message="Test error message",
            path=test_path,
        )
        assert issue.severity == ProjectIssueSeverity.ERROR
        assert issue.path == test_path

    def test_project_issue_is_frozen(self) -> None:
        """ProjectIssue is immutable (frozen dataclass)."""
        issue = ProjectIssue(
            severity=ProjectIssueSeverity.INFO,
            code="I001",
            message="Info message",
        )
        with pytest.raises(AttributeError):
            issue.code = "X999"  # type: ignore[misc]


class TestProjectFileKind:
    """Tests for ProjectFileKind enum."""

    def test_all_kind_values_exist(self) -> None:
        """All required file kind values are defined."""
        assert ProjectFileKind.FILE.value == "file"
        assert ProjectFileKind.DIRECTORY.value == "directory"
        assert ProjectFileKind.SYMLINK.value == "symlink"
        assert ProjectFileKind.OTHER.value == "other"


class TestProjectFileRole:
    """Tests for ProjectFileRole enum."""

    def test_all_role_values_exist(self) -> None:
        """All required file role values are defined."""
        assert ProjectFileRole.ROOT.value == "root"
        assert ProjectFileRole.CONFIG.value == "config"
        assert ProjectFileRole.DATA.value == "data"
        assert ProjectFileRole.SCRIPT.value == "script"
        assert ProjectFileRole.ASSET.value == "asset"
        assert ProjectFileRole.PLUGIN.value == "plugin"
        assert ProjectFileRole.METADATA.value == "metadata"
        assert ProjectFileRole.UNKNOWN.value == "unknown"


class TestProjectFile:
    """Tests for ProjectFile dataclass."""

    def test_create_project_file_minimal_required(self) -> None:
        """Can create a ProjectFile with required fields and defaults."""
        path = Path("/project/file.txt")
        relative_path = Path("file.txt")
        file_entry = ProjectFile(
            path=path,
            relative_path=relative_path,
            kind=ProjectFileKind.FILE,
            role=ProjectFileRole.UNKNOWN,
        )
        assert file_entry.path == path
        assert file_entry.relative_path == relative_path
        assert file_entry.kind == ProjectFileKind.FILE
        assert file_entry.role == ProjectFileRole.UNKNOWN
        assert file_entry.size is None
        assert file_entry.modified_at is None
        assert file_entry.is_required is False
        assert file_entry.is_present is True

    def test_create_project_file_with_optional_fields(self) -> None:
        """Can create a ProjectFile with optional fields."""
        path = Path("/project/config.json")
        relative_path = Path("config.json")
        file_entry = ProjectFile(
            path=path,
            relative_path=relative_path,
            kind=ProjectFileKind.FILE,
            role=ProjectFileRole.CONFIG,
            size=1024,
            modified_at=1234567890.0,
            is_required=True,
            is_present=True,
        )
        assert file_entry.size == 1024
        assert file_entry.modified_at == 1234567890.0
        assert file_entry.is_required is True

    def test_project_file_is_frozen(self) -> None:
        """ProjectFile is immutable (frozen dataclass)."""
        file_entry = ProjectFile(
            path=Path("/test"),
            relative_path=Path("test"),
            kind=ProjectFileKind.FILE,
            role=ProjectFileRole.UNKNOWN,
        )
        with pytest.raises(AttributeError):
            file_entry.size = 999  # type: ignore[misc]


class TestProjectStructure:
    """Tests for ProjectStructure dataclass."""

    def test_create_project_structure_minimal(self) -> None:
        """Can create a ProjectStructure with minimal fields."""
        root = Path("/project")
        structure = ProjectStructure(root=root)
        assert structure.root == root
        assert structure.entries == ()
        assert structure.relevant_files == ()
        assert structure.relevant_directories == ()

    def test_create_project_structure_with_entries(self) -> None:
        """Can create a ProjectStructure with entries."""
        root = Path("/project")
        file_entry = ProjectFile(
            path=root / "file.txt",
            relative_path=Path("file.txt"),
            kind=ProjectFileKind.FILE,
            role=ProjectFileRole.UNKNOWN,
        )
        structure = ProjectStructure(
            root=root,
            entries=(file_entry,),
            relevant_files=(root / "file.txt",),
            relevant_directories=(root / "data",),
        )
        assert len(structure.entries) == 1
        assert structure.relevant_files == (root / "file.txt",)
        assert structure.relevant_directories == (root / "data",)

    def test_project_structure_is_frozen(self) -> None:
        """ProjectStructure is immutable (frozen dataclass)."""
        structure = ProjectStructure(root=Path("/project"))
        with pytest.raises(AttributeError):
            structure.root = Path("/other")  # type: ignore[misc]


class TestProjectMetadata:
    """Tests for ProjectMetadata dataclass."""

    def test_create_project_metadata_empty(self) -> None:
        """Can create an empty ProjectMetadata."""
        metadata = ProjectMetadata()
        assert metadata.values == {}
        assert len(metadata) == 0

    def test_create_project_metadata_with_values(self) -> None:
        """Can create ProjectMetadata with initial values."""
        values = {"name": "Test Project", "version": 1, "active": True}
        metadata = ProjectMetadata(values=values)
        assert metadata["name"] == "Test Project"
        assert metadata["version"] == 1
        assert metadata["active"] is True

    def test_project_metadata_get_method(self) -> None:
        """ProjectMetadata.get() returns default for missing keys."""
        metadata = ProjectMetadata(values={"key": "value"})
        assert metadata.get("key") == "value"
        assert metadata.get("missing", "default") == "default"
        assert metadata.get("missing") is None

    def test_project_metadata_contains(self) -> None:
        """ProjectMetadata supports 'in' operator."""
        metadata = ProjectMetadata(values={"key": "value"})
        assert "key" in metadata
        assert "missing" not in metadata

    def test_project_metadata_is_frozen(self) -> None:
        """ProjectMetadata is immutable (frozen dataclass)."""
        metadata = ProjectMetadata()
        with pytest.raises(AttributeError):
            metadata.values = {"key": "value"}  # type: ignore[misc]


class TestProject:
    """Tests for Project dataclass."""

    def test_create_project_minimal(self) -> None:
        """Can create a Project with minimal fields."""
        path = Path("/project")
        project = Project(path=path)
        assert project.path == path
        assert project.engine is None
        assert project.engine_display_name is None
        assert project.engine_version is None
        assert isinstance(project.metadata, ProjectMetadata)
        assert project.structure is None
        assert project.files == ()
        assert project.status == ProjectLoadStatus.NOT_LOADED
        assert project.issues == ()
        assert project.detection is None

    def test_create_project_with_engine_info(self) -> None:
        """Can create a Project with engine information."""
        path = Path("/project")
        project = Project(
            path=path,
            engine="rpgmaker_mv",
            engine_display_name="RPG Maker MV",
            engine_version="1.6.1",
            status=ProjectLoadStatus.LOADED,
        )
        assert project.engine == "rpgmaker_mv"
        assert project.engine_display_name == "RPG Maker MV"
        assert project.engine_version == "1.6.1"
        assert project.status == ProjectLoadStatus.LOADED

    def test_create_project_with_metadata(self) -> None:
        """Can create a Project with metadata."""
        metadata = ProjectMetadata(values={"title": "My Game"})
        project = Project(path=Path("/project"), metadata=metadata)
        assert project.metadata["title"] == "My Game"

    def test_create_project_with_structure(self) -> None:
        """Can create a Project with structure."""
        structure = ProjectStructure(root=Path("/project"))
        project = Project(path=Path("/project"), structure=structure)
        assert project.structure is not None
        assert project.structure.root == Path("/project")

    def test_create_project_with_files(self) -> None:
        """Can create a Project with files tuple."""
        file_entry = ProjectFile(
            path=Path("/project/file.txt"),
            relative_path=Path("file.txt"),
            kind=ProjectFileKind.FILE,
            role=ProjectFileRole.UNKNOWN,
        )
        project = Project(path=Path("/project"), files=(file_entry,))
        assert len(project.files) == 1

    def test_create_project_with_issues(self) -> None:
        """Can create a Project with issues."""
        issue = ProjectIssue(
            severity=ProjectIssueSeverity.WARNING,
            code="W001",
            message="Warning",
        )
        project = Project(path=Path("/project"), issues=(issue,))
        assert len(project.issues) == 1

    def test_project_is_frozen(self) -> None:
        """Project is immutable (frozen dataclass)."""
        project = Project(path=Path("/project"))
        with pytest.raises(AttributeError):
            project.engine = "test"  # type: ignore[misc]


class TestProjectLoadResult:
    """Tests for ProjectLoadResult dataclass."""

    def test_create_load_result_minimal(self) -> None:
        """Can create a ProjectLoadResult with minimal fields."""
        result = ProjectLoadResult(status=ProjectLoadStatus.NOT_LOADED)
        assert result.status == ProjectLoadStatus.NOT_LOADED
        assert result.project is None
        assert result.warnings == ()
        assert result.errors == ()
        assert result.detection is None

    def test_create_load_result_with_project(self) -> None:
        """Can create a ProjectLoadResult with a project."""
        project = Project(path=Path("/project"), status=ProjectLoadStatus.LOADED)
        result = ProjectLoadResult(
            status=ProjectLoadStatus.LOADED,
            project=project,
        )
        assert result.project is not None
        assert result.project.path == Path("/project")

    def test_create_load_result_with_warnings_and_errors(self) -> None:
        """Can create a ProjectLoadResult with warnings and errors."""
        warning = ProjectIssue(
            severity=ProjectIssueSeverity.WARNING,
            code="W001",
            message="Warning message",
        )
        error = ProjectIssue(
            severity=ProjectIssueSeverity.ERROR,
            code="E001",
            message="Error message",
        )
        result = ProjectLoadResult(
            status=ProjectLoadStatus.INCOMPLETE,
            warnings=(warning,),
            errors=(error,),
        )
        assert len(result.warnings) == 1
        assert len(result.errors) == 1
        assert result.warnings[0].severity == ProjectIssueSeverity.WARNING
        assert result.errors[0].severity == ProjectIssueSeverity.ERROR

    def test_load_result_is_frozen(self) -> None:
        """ProjectLoadResult is immutable (frozen dataclass)."""
        result = ProjectLoadResult(status=ProjectLoadStatus.NOT_LOADED)
        with pytest.raises(AttributeError):
            result.status = ProjectLoadStatus.LOADED  # type: ignore[misc]
