"""Translation pipeline orchestration for RPG Translator Suite.

This module implements the TranslationPipeline class that coordinates
the translation process, handling validation, error isolation, and
batch processing without knowing about specific translator implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from app.core.translation import (
        TranslationBatchResult,
        TranslationEntry,
        TranslationIssue,
        TranslationResult,
        Translator,
    )


class TranslationPipeline:
    """Orchestrates translation of multiple entries through a Translator.

    The pipeline is responsible for:
    - Receiving translation entries
    - Validating entries minimally
    - Calling the Translator for each entry
    - Collecting results
    - Ensuring one failure doesn't stop the entire batch
    - Producing a TranslationBatchResult

    The pipeline remains engine-independent and knows nothing about
    specific translator implementations (Qwen, OpenAI, etc.).
    """

    def __init__(self, translator: Translator) -> None:
        """Initialize the pipeline with a translator.

        Args:
            translator: The Translator implementation to use for translations.
        """
        self._translator = translator

    def _validate_entry(self, entry: TranslationEntry) -> tuple[bool, TranslationIssue | None]:
        """Validate a translation entry minimally.

        Args:
            entry: The entry to validate.

        Returns:
            A tuple of (is_valid, issue). If valid, issue is None.
            If invalid, issue describes why.
        """
        from app.core.translation import TranslationIssue, TranslationIssueSeverity

        # Check for empty ID
        if not entry.id or not entry.id.strip():
            return False, TranslationIssue(
                severity=TranslationIssueSeverity.ERROR,
                code="invalid_entry",
                message="Entry ID is empty or whitespace-only",
                entry_id=entry.id if entry.id else None,
                source_file=entry.source_file,
            )

        # Check for empty original_text
        if not entry.original_text:
            return False, TranslationIssue(
                severity=TranslationIssueSeverity.WARNING,
                code="empty_source",
                message="Original text is empty",
                entry_id=entry.id,
                source_file=entry.source_file,
            )

        return True, None

    def translate(self, entries: Sequence[TranslationEntry]) -> TranslationBatchResult:
        """Translate a batch of entries.

        Args:
            entries: Sequence of TranslationEntry objects to translate.

        Returns:
            A TranslationBatchResult containing all individual results and
            any batch-level issues.

        Notes:
            - Each entry is processed independently
            - A failure in one entry does not stop processing of others
            - Invalid entries are marked as INVALID without calling the translator
            - Exceptions from the translator are caught and converted to FAILED status
        """
        from app.core.translation import (
            TranslationBatchResult,
            TranslationIssue,
            TranslationIssueSeverity,
            TranslationResult,
            TranslationStatus,
        )

        results: list[TranslationResult] = []
        batch_issues: list[TranslationIssue] = []

        for entry in entries:
            # Validate entry first
            is_valid, validation_issue = self._validate_entry(entry)

            if not is_valid:
                # Entry is invalid - don't call translator
                assert validation_issue is not None
                results.append(TranslationResult(
                    entry_id=entry.id,
                    status=TranslationStatus.INVALID,
                    original_text=entry.original_text,
                    translated_text=None,
                    translator=None,
                    issues=(validation_issue,),
                ))
                continue

            # Call the translator
            try:
                result = self._translator.translate(entry)
                results.append(result)
            except Exception as exc:  # noqa: BLE001
                # Translator failed unexpectedly - convert to FAILED status
                issue = TranslationIssue(
                    severity=TranslationIssueSeverity.ERROR,
                    code="translator_failed",
                    message=f"Translator raised an exception: {type(exc).__name__}: {exc}",
                    entry_id=entry.id,
                    source_file=entry.source_file,
                )
                results.append(TranslationResult(
                    entry_id=entry.id,
                    status=TranslationStatus.FAILED,
                    original_text=entry.original_text,
                    translated_text=None,
                    translator=self._translator.translator_id if hasattr(self._translator, 'translator_id') else None,
                    issues=(issue,),
                ))

        return TranslationBatchResult(
            results=tuple(results),
            issues=tuple(batch_issues),
        )
