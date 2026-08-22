"""Tests for the data extraction API models."""

from pathlib import Path

import pytest

from app.core.extraction import (
    ExtractionEntry,
    ExtractionEntryType,
    ExtractionIssue,
    ExtractionIssueSeverity,
    ExtractionResult,
    ExtractionStatus,
)


class TestExtractionStatus:
    """Tests for ExtractionStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert ExtractionStatus.EXTRACTED.value == "extracted"
        assert ExtractionStatus.PARTIAL.value == "partial"
        assert ExtractionStatus.NOT_SUPPORTED.value == "not_supported"
        assert ExtractionStatus.INVALID_PROJECT.value == "invalid_project"
        assert ExtractionStatus.READ_ERROR.value == "read_error"
        assert ExtractionStatus.FAILED.value == "failed"

    def test_status_is_string_enum(self):
        """Test that status is a string enum."""
        assert isinstance(ExtractionStatus.EXTRACTED, str)
        assert ExtractionStatus.EXTRACTED == "extracted"


class TestExtractionIssueSeverity:
    """Tests for ExtractionIssueSeverity enum."""

    def test_severity_values(self):
        """Test all severity values exist."""
        assert ExtractionIssueSeverity.INFO.value == "info"
        assert ExtractionIssueSeverity.WARNING.value == "warning"
        assert ExtractionIssueSeverity.ERROR.value == "error"

    def test_severity_is_string_enum(self):
        """Test that severity is a string enum."""
        assert isinstance(ExtractionIssueSeverity.INFO, str)
        assert ExtractionIssueSeverity.INFO == "info"


class TestExtractionIssue:
    """Tests for ExtractionIssue dataclass."""

    def test_create_issue_minimal(self):
        """Test creating an issue with minimal fields."""
        issue = ExtractionIssue(
            severity=ExtractionIssueSeverity.ERROR,
            code="test_code",
            message="Test message",
        )
        assert issue.severity == ExtractionIssueSeverity.ERROR
        assert issue.code == "test_code"
        assert issue.message == "Test message"
        assert issue.path is None

    def test_create_issue_with_path(self):
        """Test creating an issue with a path."""
        path = Path("some/path/file.json")
        issue = ExtractionIssue(
            severity=ExtractionIssueSeverity.WARNING,
            code="missing_file",
            message="File not found",
            path=path,
        )
        assert issue.path == path

    def test_issue_is_frozen(self):
        """Test that ExtractionIssue is immutable."""
        issue = ExtractionIssue(
            severity=ExtractionIssueSeverity.INFO,
            code="info_code",
            message="Info message",
        )
        with pytest.raises(AttributeError):
            issue.code = "new_code"  # type: ignore[misc]


class TestExtractionEntryType:
    """Tests for ExtractionEntryType enum."""

    def test_entry_type_values(self):
        """Test all entry type values exist."""
        assert ExtractionEntryType.TEXT.value == "text"
        assert ExtractionEntryType.NAME.value == "name"
        assert ExtractionEntryType.DESCRIPTION.value == "description"
        assert ExtractionEntryType.MESSAGE.value == "message"
        assert ExtractionEntryType.OTHER.value == "other"

    def test_entry_type_is_string_enum(self):
        """Test that entry type is a string enum."""
        assert isinstance(ExtractionEntryType.TEXT, str)
        assert ExtractionEntryType.TEXT == "text"


class TestExtractionEntry:
    """Tests for ExtractionEntry dataclass."""

    def test_create_entry_minimal(self):
        """Test creating an entry with minimal fields."""
        entry = ExtractionEntry(
            entry_id="test:id",
            entry_type=ExtractionEntryType.TEXT,
            text="Some text",
            source_path=Path("file.txt"),
        )
        assert entry.entry_id == "test:id"
        assert entry.entry_type == ExtractionEntryType.TEXT
        assert entry.text == "Some text"
        assert entry.source_path == Path("file.txt")
        assert entry.metadata == {}

    def test_create_entry_with_metadata(self):
        """Test creating an entry with metadata."""
        metadata = {"key1": "value1", "key2": 42, "key3": True}
        entry = ExtractionEntry(
            entry_id="test:id",
            entry_type=ExtractionEntryType.NAME,
            text="Name text",
            source_path=Path("data.json"),
            metadata=metadata,
        )
        assert entry.metadata["key1"] == "value1"
        assert entry.metadata["key2"] == 42
        assert entry.metadata["key3"] is True

    def test_entry_is_frozen(self):
        """Test that ExtractionEntry is immutable."""
        entry = ExtractionEntry(
            entry_id="test:id",
            entry_type=ExtractionEntryType.TEXT,
            text="Text",
            source_path=Path("file.txt"),
        )
        with pytest.raises(AttributeError):
            entry.text = "new text"  # type: ignore[misc]

    def test_entry_default_metadata_is_empty_dict(self):
        """Test that default metadata is an empty dict."""
        entry = ExtractionEntry(
            entry_id="test:id",
            entry_type=ExtractionEntryType.TEXT,
            text="Text",
            source_path=Path("file.txt"),
        )
        assert entry.metadata == {}
        # Ensure each instance gets its own dict
        entry2 = ExtractionEntry(
            entry_id="test:id2",
            entry_type=ExtractionEntryType.TEXT,
            text="Text2",
            source_path=Path("file2.txt"),
        )
        assert entry.metadata is not entry2.metadata


class TestExtractionResult:
    """Tests for ExtractionResult dataclass."""

    def test_create_result_minimal(self):
        """Test creating a result with minimal fields."""
        result = ExtractionResult(status=ExtractionStatus.EXTRACTED)
        assert result.status == ExtractionStatus.EXTRACTED
        assert result.entries == ()
        assert result.warnings == ()
        assert result.errors == ()
        assert result.project is None

    def test_create_result_with_entries(self):
        """Test creating a result with entries."""
        entry = ExtractionEntry(
            entry_id="test:id",
            entry_type=ExtractionEntryType.TEXT,
            text="Text",
            source_path=Path("file.txt"),
        )
        result = ExtractionResult(
            status=ExtractionStatus.EXTRACTED,
            entries=(entry,),
        )
        assert len(result.entries) == 1
        assert result.entries[0] == entry

    def test_create_result_with_issues(self):
        """Test creating a result with warnings and errors."""
        warning = ExtractionIssue(
            severity=ExtractionIssueSeverity.WARNING,
            code="warn_code",
            message="Warning",
        )
        error = ExtractionIssue(
            severity=ExtractionIssueSeverity.ERROR,
            code="err_code",
            message="Error",
        )
        result = ExtractionResult(
            status=ExtractionStatus.PARTIAL,
            warnings=(warning,),
            errors=(error,),
        )
        assert len(result.warnings) == 1
        assert len(result.errors) == 1

    def test_result_is_frozen(self):
        """Test that ExtractionResult is immutable."""
        result = ExtractionResult(status=ExtractionStatus.EXTRACTED)
        with pytest.raises(AttributeError):
            result.status = ExtractionStatus.FAILED  # type: ignore[misc]

    def test_create_result_with_project(self):
        """Test creating a result with a project reference."""
        from app.core.project_model import Project, ProjectLoadStatus

        project = Project(
            path=Path("/test/project"),
            status=ProjectLoadStatus.LOADED,
        )
        result = ExtractionResult(
            status=ExtractionStatus.EXTRACTED,
            project=project,
        )
        assert result.project is project
