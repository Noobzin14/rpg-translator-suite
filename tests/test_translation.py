"""Tests for translation pipeline models."""

from pathlib import Path

import pytest

from app.core.translation import (
    TranslationBatchResult,
    TranslationEntry,
    TranslationIssue,
    TranslationIssueSeverity,
    TranslationResult,
    TranslationStatus,
)


class TestTranslationStatus:
    """Test TranslationStatus enum."""

    def test_status_values(self):
        """Test that all status values exist."""
        assert TranslationStatus.PENDING.value == "pending"
        assert TranslationStatus.TRANSLATED.value == "translated"
        assert TranslationStatus.SKIPPED.value == "skipped"
        assert TranslationStatus.FAILED.value == "failed"
        assert TranslationStatus.INVALID.value == "invalid"

    def test_status_is_string_enum(self):
        """Test that TranslationStatus is a string enum."""
        assert isinstance(TranslationStatus.PENDING, str)
        assert TranslationStatus.TRANSLATED == "translated"


class TestTranslationIssueSeverity:
    """Test TranslationIssueSeverity enum."""

    def test_severity_values(self):
        """Test that all severity levels exist."""
        assert TranslationIssueSeverity.INFO.value == "info"
        assert TranslationIssueSeverity.WARNING.value == "warning"
        assert TranslationIssueSeverity.ERROR.value == "error"

    def test_severity_is_string_enum(self):
        """Test that TranslationIssueSeverity is a string enum."""
        assert isinstance(TranslationIssueSeverity.INFO, str)


class TestTranslationIssue:
    """Test TranslationIssue dataclass."""

    def test_create_issue_minimal(self):
        """Test creating an issue with minimal fields."""
        issue = TranslationIssue(
            severity=TranslationIssueSeverity.WARNING,
            code="empty_source",
            message="Original text is empty",
        )
        assert issue.severity == TranslationIssueSeverity.WARNING
        assert issue.code == "empty_source"
        assert issue.message == "Original text is empty"
        assert issue.entry_id is None
        assert issue.source_file is None

    def test_create_issue_full(self):
        """Test creating an issue with all fields."""
        source_path = Path("test/file.json")
        issue = TranslationIssue(
            severity=TranslationIssueSeverity.ERROR,
            code="translator_failed",
            message="Translation failed",
            entry_id="entry_001",
            source_file=source_path,
        )
        assert issue.severity == TranslationIssueSeverity.ERROR
        assert issue.code == "translator_failed"
        assert issue.message == "Translation failed"
        assert issue.entry_id == "entry_001"
        assert issue.source_file == source_path

    def test_issue_is_frozen(self):
        """Test that TranslationIssue is immutable."""
        issue = TranslationIssue(
            severity=TranslationIssueSeverity.INFO,
            code="test_code",
            message="Test message",
        )
        with pytest.raises(AttributeError):
            issue.code = "new_code"  # type: ignore[misc]


class TestTranslationResult:
    """Test TranslationResult dataclass."""

    def test_create_result_translated(self):
        """Test creating a result with TRANSLATED status."""
        result = TranslationResult(
            entry_id="entry_001",
            status=TranslationStatus.TRANSLATED,
            original_text="Hello, world!",
            translated_text="Olá, mundo!",
            translator="fake",
        )
        assert result.entry_id == "entry_001"
        assert result.status == TranslationStatus.TRANSLATED
        assert result.original_text == "Hello, world!"
        assert result.translated_text == "Olá, mundo!"
        assert result.translator == "fake"
        assert result.issues == ()

    def test_create_result_with_issues(self):
        """Test creating a result with issues."""
        issue = TranslationIssue(
            severity=TranslationIssueSeverity.WARNING,
            code="placeholder_warning",
            message="Placeholder found",
        )
        result = TranslationResult(
            entry_id="entry_001",
            status=TranslationStatus.TRANSLATED,
            original_text="Hello %1!",
            translated_text="Olá %1!",
            translator="fake",
            issues=(issue,),
        )
        assert len(result.issues) == 1
        assert result.issues[0].code == "placeholder_warning"

    def test_create_result_no_translation(self):
        """Test creating a result without translation."""
        result = TranslationResult(
            entry_id="entry_001",
            status=TranslationStatus.FAILED,
            original_text="Hello, world!",
            translated_text=None,
        )
        assert result.status == TranslationStatus.FAILED
        assert result.translated_text is None

    def test_original_text_preserved_exactly(self):
        """Test that original_text is preserved exactly."""
        # Test with special characters and unicode
        original = "Olá, 日本語，한국어, é, ç, %1, \\n"
        result = TranslationResult(
            entry_id="entry_001",
            status=TranslationStatus.TRANSLATED,
            original_text=original,
            translated_text="Translated",
        )
        assert result.original_text == original

    def test_result_is_frozen(self):
        """Test that TranslationResult is immutable."""
        result = TranslationResult(
            entry_id="entry_001",
            status=TranslationStatus.PENDING,
            original_text="Test",
        )
        with pytest.raises(AttributeError):
            result.status = TranslationStatus.TRANSLATED  # type: ignore[misc]

    def test_defaults(self):
        """Test default values."""
        result = TranslationResult(
            entry_id="entry_001",
            status=TranslationStatus.PENDING,
            original_text="Test",
        )
        assert result.translated_text is None
        assert result.translator is None
        assert result.issues == ()


class TestTranslationBatchResult:
    """Test TranslationBatchResult dataclass."""

    def test_create_batch_empty(self):
        """Test creating an empty batch result."""
        batch = TranslationBatchResult(results=())
        assert batch.results == ()
        assert batch.issues == ()

    def test_create_batch_with_results(self):
        """Test creating a batch with results."""
        result1 = TranslationResult(
            entry_id="entry_001",
            status=TranslationStatus.TRANSLATED,
            original_text="Hello",
            translated_text="Olá",
        )
        result2 = TranslationResult(
            entry_id="entry_002",
            status=TranslationStatus.FAILED,
            original_text="World",
        )
        batch = TranslationBatchResult(results=(result1, result2))
        assert len(batch.results) == 2
        assert batch.results[0].entry_id == "entry_001"
        assert batch.results[1].entry_id == "entry_002"

    def test_create_batch_with_issues(self):
        """Test creating a batch with batch-level issues."""
        issue = TranslationIssue(
            severity=TranslationIssueSeverity.INFO,
            code="batch_info",
            message="Batch processed",
        )
        batch = TranslationBatchResult(
            results=(),
            issues=(issue,),
        )
        assert len(batch.issues) == 1
        assert batch.issues[0].code == "batch_info"

    def test_batch_is_frozen(self):
        """Test that TranslationBatchResult is immutable."""
        batch = TranslationBatchResult(results=())
        with pytest.raises(AttributeError):
            batch.results = (  # type: ignore[misc]
                TranslationResult(
                    entry_id="x",
                    status=TranslationStatus.PENDING,
                    original_text="x",
                ),
            )


class TestTranslationEntry:
    """Test TranslationEntry dataclass."""

    def test_create_entry_minimal(self):
        """Test creating an entry with minimal fields."""
        entry = TranslationEntry(
            id="entry_001",
            original_text="Hello, world!",
        )
        assert entry.id == "entry_001"
        assert entry.original_text == "Hello, world!"
        assert entry.context is None
        assert entry.metadata == {}
        assert entry.source_file is None

    def test_create_entry_full(self):
        """Test creating an entry with all fields."""
        source_path = Path("test/file.json")
        entry = TranslationEntry(
            id="entry_001",
            original_text="Hello, world!",
            context="dialogue",
            metadata={"speaker": "Hero", "map_id": 1},
            source_file=source_path,
        )
        assert entry.id == "entry_001"
        assert entry.original_text == "Hello, world!"
        assert entry.context == "dialogue"
        assert entry.metadata == {"speaker": "Hero", "map_id": 1}
        assert entry.source_file == source_path

    def test_entry_is_frozen(self):
        """Test that TranslationEntry is immutable."""
        entry = TranslationEntry(
            id="entry_001",
            original_text="Test",
        )
        with pytest.raises(AttributeError):
            entry.original_text = "New text"  # type: ignore[misc]

    def test_original_text_preserved_exactly(self):
        """Test that original_text is preserved exactly without modification."""
        # Test with placeholders
        original_with_placeholder = "Hello, %1!"
        entry = TranslationEntry(
            id="entry_001",
            original_text=original_with_placeholder,
        )
        assert entry.original_text == original_with_placeholder

        # Test with unicode
        original_unicode = "Olá, 日本語，한국어"
        entry_unicode = TranslationEntry(
            id="entry_002",
            original_text=original_unicode,
        )
        assert entry_unicode.original_text == original_unicode

        # Test with escape sequences
        original_escape = "Line1\\nLine2"
        entry_escape = TranslationEntry(
            id="entry_003",
            original_text=original_escape,
        )
        assert entry_escape.original_text == original_escape

    def test_metadata_default_factory(self):
        """Test that metadata uses default factory."""
        entry1 = TranslationEntry(id="1", original_text="A")
        entry2 = TranslationEntry(id="2", original_text="B")
        # Should be different instances
        entry1.metadata["key"] = "value"
        assert entry2.metadata == {}
        assert entry1.metadata == {"key": "value"}
