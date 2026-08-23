"""Tests for translation pipeline and translator interface."""

from pathlib import Path

import pytest

from app.core.translation import (
    TranslationEntry,
    TranslationIssue,
    TranslationIssueSeverity,
    TranslationResult,
    TranslationStatus,
    Translator,
)
from app.core.translation_pipeline import TranslationPipeline


class FakeTranslator(Translator):
    """Fake translator for testing purposes.

    This translator simply prefixes the original text with "TR:"
    to simulate a translation without using any real translation service.
    """

    @property
    def translator_id(self) -> str:
        """Return the fake translator identifier."""
        return "fake"

    def translate(self, entry: TranslationEntry) -> TranslationResult:
        """Translate an entry by prefixing with 'TR:'."""
        return TranslationResult(
            entry_id=entry.id,
            status=TranslationStatus.TRANSLATED,
            original_text=entry.original_text,
            translated_text=f"TR:{entry.original_text}",
            translator=self.translator_id,
        )


class FakeSkippingTranslator(Translator):
    """Fake translator that skips all entries."""

    @property
    def translator_id(self) -> str:
        return "fake_skipper"

    def translate(self, entry: TranslationEntry) -> TranslationResult:
        return TranslationResult(
            entry_id=entry.id,
            status=TranslationStatus.SKIPPED,
            original_text=entry.original_text,
            translated_text=None,
            translator=self.translator_id,
            issues=(TranslationIssue(
                severity=TranslationIssueSeverity.INFO,
                code="translator_skipped",
                message="Translator chose to skip this entry",
                entry_id=entry.id,
            ),),
        )


class FakeFailingTranslator(Translator):
    """Fake translator that fails all entries."""

    @property
    def translator_id(self) -> str:
        return "fake_failer"

    def translate(self, entry: TranslationEntry) -> TranslationResult:
        return TranslationResult(
            entry_id=entry.id,
            status=TranslationStatus.FAILED,
            original_text=entry.original_text,
            translated_text=None,
            translator=self.translator_id,
            issues=(TranslationIssue(
                severity=TranslationIssueSeverity.ERROR,
                code="translator_failed",
                message="Deliberate failure for testing",
                entry_id=entry.id,
            ),),
        )


class FakeExceptionTranslator(Translator):
    """Fake translator that raises exceptions."""

    @property
    def translator_id(self) -> str:
        return "fake_exception"

    def translate(self, entry: TranslationEntry) -> TranslationResult:
        raise RuntimeError("Simulated translator crash")


class TestFakeTranslator:
    """Test the FakeTranslator implementation."""

    def test_translator_id(self):
        """Test translator_id property."""
        translator = FakeTranslator()
        assert translator.translator_id == "fake"

    def test_translate_preserves_entry_id(self):
        """Test that entry_id is preserved in result."""
        translator = FakeTranslator()
        entry = TranslationEntry(id="test_123", original_text="Hello")
        result = translator.translate(entry)
        assert result.entry_id == "test_123"

    def test_translate_preserves_original_text(self):
        """Test that original_text is preserved exactly."""
        translator = FakeTranslator()
        original = "Hello, %1! Olá, 日本語"
        entry = TranslationEntry(id="1", original_text=original)
        result = translator.translate(entry)
        assert result.original_text == original

    def test_translate_returns_translated(self):
        """Test that translation returns TRANSLATED status."""
        translator = FakeTranslator()
        entry = TranslationEntry(id="1", original_text="Hello")
        result = translator.translate(entry)
        assert result.status == TranslationStatus.TRANSLATED
        assert result.translated_text == "TR:Hello"


class TestTranslationPipeline:
    """Test TranslationPipeline behavior."""

    def test_pipeline_with_fake_translator(self):
        """Test pipeline processes entries with fake translator."""
        translator = FakeTranslator()
        pipeline = TranslationPipeline(translator)
        entry = TranslationEntry(id="1", original_text="Hello")
        batch = pipeline.translate([entry])
        assert len(batch.results) == 1
        assert batch.results[0].status == TranslationStatus.TRANSLATED
        assert batch.results[0].translated_text == "TR:Hello"

    def test_pipeline_multiple_entries(self):
        """Test pipeline processes multiple entries."""
        translator = FakeTranslator()
        pipeline = TranslationPipeline(translator)
        entries = [
            TranslationEntry(id="1", original_text="Hello"),
            TranslationEntry(id="2", original_text="World"),
            TranslationEntry(id="3", original_text="Test"),
        ]
        batch = pipeline.translate(entries)
        assert len(batch.results) == 3
        assert all(r.status == TranslationStatus.TRANSLATED for r in batch.results)

    def test_pipeline_empty_source_invalid(self):
        """Test that empty original_text results in INVALID status."""
        translator = FakeTranslator()
        pipeline = TranslationPipeline(translator)
        entry = TranslationEntry(id="1", original_text="")
        batch = pipeline.translate([entry])
        assert len(batch.results) == 1
        assert batch.results[0].status == TranslationStatus.INVALID
        assert any(issue.code == "empty_source" for issue in batch.results[0].issues)

    def test_pipeline_empty_id_invalid(self):
        """Test that empty ID results in INVALID status."""
        translator = FakeTranslator()
        pipeline = TranslationPipeline(translator)
        entry = TranslationEntry(id="", original_text="Hello")
        batch = pipeline.translate([entry])
        assert len(batch.results) == 1
        assert batch.results[0].status == TranslationStatus.INVALID
        assert any(issue.code == "invalid_entry" for issue in batch.results[0].issues)

    def test_pipeline_whitespace_id_invalid(self):
        """Test that whitespace-only ID results in INVALID status."""
        translator = FakeTranslator()
        pipeline = TranslationPipeline(translator)
        entry = TranslationEntry(id="   ", original_text="Hello")
        batch = pipeline.translate([entry])
        assert len(batch.results) == 1
        assert batch.results[0].status == TranslationStatus.INVALID

    def test_pipeline_preserves_skipped_status(self):
        """Test that SKIPPED status from translator is preserved."""
        translator = FakeSkippingTranslator()
        pipeline = TranslationPipeline(translator)
        entry = TranslationEntry(id="1", original_text="Hello")
        batch = pipeline.translate([entry])
        assert len(batch.results) == 1
        assert batch.results[0].status == TranslationStatus.SKIPPED

    def test_pipeline_preserves_failed_status(self):
        """Test that FAILED status from translator is preserved."""
        translator = FakeFailingTranslator()
        pipeline = TranslationPipeline(translator)
        entry = TranslationEntry(id="1", original_text="Hello")
        batch = pipeline.translate([entry])
        assert len(batch.results) == 1
        assert batch.results[0].status == TranslationStatus.FAILED

    def test_pipeline_translator_exception_becomes_failed(self):
        """Test that translator exceptions are converted to FAILED status."""
        translator = FakeExceptionTranslator()
        pipeline = TranslationPipeline(translator)
        entry = TranslationEntry(id="1", original_text="Hello")
        batch = pipeline.translate([entry])
        assert len(batch.results) == 1
        assert batch.results[0].status == TranslationStatus.FAILED
        assert any(issue.code == "translator_failed" for issue in batch.results[0].issues)

    def test_pipeline_one_failure_doesnt_stop_others(self):
        """Test that one failing entry doesn't stop processing of others."""
        entries = [
            TranslationEntry(id="1", original_text="Hello"),
            TranslationEntry(id="2", original_text=""),  # Will be invalid
            TranslationEntry(id="3", original_text="World"),
        ]
        translator = FakeTranslator()
        pipeline = TranslationPipeline(translator)
        batch = pipeline.translate(entries)
        # All three entries should be in results
        assert len(batch.results) == 3
        # First should be translated
        assert batch.results[0].status == TranslationStatus.TRANSLATED
        # Second should be invalid
        assert batch.results[1].status == TranslationStatus.INVALID
        # Third should be translated
        assert batch.results[2].status == TranslationStatus.TRANSLATED

    def test_pipeline_partial_failure_batch(self):
        """Test batch with mixed success/failure results."""
        # Create a custom translator that fails on specific IDs
        class SelectiveFailingTranslator(Translator):
            @property
            def translator_id(self) -> str:
                return "selective_failer"

            def translate(self, entry: TranslationEntry) -> TranslationResult:
                if entry.id == "2":
                    raise RuntimeError("Fail entry 2")
                return TranslationResult(
                    entry_id=entry.id,
                    status=TranslationStatus.TRANSLATED,
                    original_text=entry.original_text,
                    translated_text=f"TR:{entry.original_text}",
                    translator=self.translator_id,
                )

        entries = [
            TranslationEntry(id="1", original_text="Hello"),
            TranslationEntry(id="2", original_text="Fail"),
            TranslationEntry(id="3", original_text="World"),
        ]
        translator = SelectiveFailingTranslator()
        pipeline = TranslationPipeline(translator)
        batch = pipeline.translate(entries)

        assert len(batch.results) == 3
        assert batch.results[0].status == TranslationStatus.TRANSLATED
        assert batch.results[1].status == TranslationStatus.FAILED
        assert batch.results[2].status == TranslationStatus.TRANSLATED

    def test_pipeline_preserves_placeholders(self):
        """Test that placeholders are delivered to translator unchanged."""
        translator = FakeTranslator()
        pipeline = TranslationPipeline(translator)
        original = "Hello, %1!"
        entry = TranslationEntry(id="1", original_text=original)
        batch = pipeline.translate([entry])
        # The fake translator prefixes with "TR:", so we check the original is preserved
        assert batch.results[0].original_text == original
        assert "%1" in batch.results[0].original_text

    def test_pipeline_preserves_unicode(self):
        """Test that unicode characters are preserved without alteration."""
        translator = FakeTranslator()
        pipeline = TranslationPipeline(translator)
        original = "Olá, 日本語，한국어, é, ç"
        entry = TranslationEntry(id="1", original_text=original)
        batch = pipeline.translate([entry])
        assert batch.results[0].original_text == original

    def test_pipeline_empty_batch(self):
        """Test pipeline with empty input."""
        translator = FakeTranslator()
        pipeline = TranslationPipeline(translator)
        batch = pipeline.translate([])
        assert batch.results == ()
        assert batch.issues == ()

    def test_pipeline_original_text_never_modified(self):
        """Test that original_text is never modified by the pipeline."""
        translator = FakeTranslator()
        pipeline = TranslationPipeline(translator)

        test_cases = [
            "Hello, world!",
            "Hello, %1!",
            "Olá, 日本語",
            "Line1\\nLine2",
            "  Spaces  ",  # Should preserve leading/trailing spaces
        ]

        for original in test_cases:
            entry = TranslationEntry(id="1", original_text=original)
            batch = pipeline.translate([entry])
            assert batch.results[0].original_text == original


class TestTranslatorInterface:
    """Test that Translator interface is properly defined."""

    def test_translator_is_abstract(self):
        """Test that Translator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Translator()  # type: ignore[abstract]

    def test_translator_requires_translate_method(self):
        """Test that Translator requires translate method implementation."""
        class IncompleteTranslator(Translator):
            @property
            def translator_id(self) -> str:
                return "incomplete"

        with pytest.raises(TypeError):
            IncompleteTranslator()

    def test_translator_requires_translator_id_property(self):
        """Test that Translator requires translator_id property implementation."""
        class IncompleteTranslator2(Translator):
            def translate(self, entry: TranslationEntry) -> TranslationResult:
                return TranslationResult(
                    entry_id=entry.id,
                    status=TranslationStatus.PENDING,
                    original_text=entry.original_text,
                )

        with pytest.raises(TypeError):
            IncompleteTranslator2()
