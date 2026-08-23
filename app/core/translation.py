"""Translation pipeline models and interfaces for RPG Translator Suite.

This module defines the engine-independent translation pipeline API,
including data models, status enums, and the abstract Translator interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from app.core.extraction import ExtractionEntry


class TranslationStatus(str, Enum):
    """Possible statuses for a translation entry.

    Attributes:
        PENDING: Entry has not been processed yet.
        TRANSLATED: A valid translation exists for the original text.
        SKIPPED: Entry was deliberately ignored by the pipeline/translator.
        FAILED: Translation attempt failed.
        INVALID: Entry cannot be processed due to structural invalidity.
    """

    PENDING = "pending"
    TRANSLATED = "translated"
    SKIPPED = "skipped"
    FAILED = "failed"
    INVALID = "invalid"


class TranslationIssueSeverity(str, Enum):
    """Severity levels for translation issues.

    Attributes:
        INFO: Informational message, no action required.
        WARNING: Non-blocking issue that should be reviewed.
        ERROR: Blocking issue that prevented translation.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class TranslationIssue:
    """Represents an issue found during translation.

    Attributes:
        severity: The severity level of this issue.
        code: A machine-readable code identifying the issue type.
        message: A human-readable description of the issue.
        entry_id: Optional ID of the related translation entry.
        source_file: Optional path to the source file related to this issue.
    """

    severity: TranslationIssueSeverity
    code: str
    message: str
    entry_id: str | None = None
    source_file: Path | None = None


@dataclass(frozen=True)
class TranslationResult:
    """Result of translating a single entry.

    Attributes:
        entry_id: Identifier of the translated entry.
        status: The translation status for this entry.
        original_text: The original text (preserved exactly as received).
        translated_text: The translated text (None if not translated).
        translator: Optional identifier of the translator used.
        issues: Tuple of issues encountered during translation.
    """

    entry_id: str
    status: TranslationStatus
    original_text: str
    translated_text: str | None = None
    translator: str | None = None
    issues: tuple[TranslationIssue, ...] = ()


@dataclass(frozen=True)
class TranslationBatchResult:
    """Aggregated result of translating multiple entries.

    Attributes:
        results: Tuple of individual translation results.
        issues: Tuple of batch-level issues (not tied to specific entries).
    """

    results: tuple[TranslationResult, ...]
    issues: tuple[TranslationIssue, ...] = ()


# Import ExtractionEntry here to avoid circular imports at module load time
def _get_extraction_entry():
    """Lazy import to avoid circular dependency."""
    from app.core.extraction import ExtractionEntry
    return ExtractionEntry


@dataclass(frozen=True)
class TranslationEntry:
    """Represents a single text entry ready for translation.

    This is the bridge between extraction and translation phases.
    It contains only the information needed for translation, remaining
    engine-independent.

    Attributes:
        id: A stable identifier for this entry within the translation batch.
        original_text: The text content to be translated (preserved exactly).
        context: Optional contextual information about where this text appears.
        metadata: Optional key-value pairs with additional information.
        source_file: Optional path to the source file (for context/issues).
    """

    id: str
    original_text: str
    context: str | None = None
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)
    source_file: Path | None = None

    @classmethod
    def from_extraction_entry(cls, entry: ExtractionEntry) -> TranslationEntry:
        """Create a TranslationEntry from an ExtractionEntry.

        Args:
            entry: The extraction entry to convert.

        Returns:
            A new TranslationEntry with data from the extraction entry.
        """
        return cls(
            id=entry.entry_id,
            original_text=entry.text,
            context=f"{entry.entry_type.value}",
            metadata=dict(entry.metadata) if entry.metadata else {},
            source_file=entry.source_path,
        )


class Translator(ABC):
    """Abstract base class for translation engines.

    This interface defines the contract that all translator implementations
    must follow. The Core remains engine-independent by only knowing about
    this abstract interface.

    Concrete implementations (QwenTranslator, OpenAITranslator, etc.)
    belong in separate modules/plugins and are NOT part of the Core.
    """

    @property
    @abstractmethod
    def translator_id(self) -> str:
        """Return a unique identifier for this translator.

        Examples: 'qwen', 'openai', 'claude', 'manual', 'local'
        """
        pass

    @abstractmethod
    def translate(self, entry: TranslationEntry) -> TranslationResult:
        """Translate a single entry.

        Args:
            entry: The translation entry to process.

        Returns:
            A TranslationResult containing the translation outcome.

        Notes:
            - Must not modify the original entry.
            - Must preserve original_text exactly.
            - Should handle exceptions gracefully.
            - Must not write to files or external services (in this stage).
        """
        pass
