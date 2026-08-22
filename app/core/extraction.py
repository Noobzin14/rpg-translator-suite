"""Data extraction models for RPG Translator Suite."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from app.core.project_model import Project


class ExtractionStatus(str, Enum):
    """Possible statuses for a data extraction operation."""

    EXTRACTED = "extracted"
    PARTIAL = "partial"
    NOT_SUPPORTED = "not_supported"
    INVALID_PROJECT = "invalid_project"
    READ_ERROR = "read_error"
    FAILED = "failed"


class ExtractionIssueSeverity(str, Enum):
    """Severity levels for extraction issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ExtractionIssue:
    """Represents an issue found during data extraction.

    Attributes:
        severity: The severity level of this issue.
        code: A machine-readable code identifying the issue type.
        message: A human-readable description of the issue.
        path: Optional path related to this issue.
    """

    severity: ExtractionIssueSeverity
    code: str
    message: str
    path: Path | None = None


class ExtractionEntryType(str, Enum):
    """Generic types for extracted text entries.

    These types are conceptual and engine-independent. Engine-specific
    entry types belong in plugin implementations.
    """

    TEXT = "text"
    NAME = "name"
    DESCRIPTION = "description"
    MESSAGE = "message"
    OTHER = "other"


@dataclass(frozen=True)
class ExtractionEntry:
    """Represents a single extracted text entry.

    Attributes:
        entry_id: A stable identifier for this entry within the extraction.
        entry_type: The conceptual type of this text entry.
        text: The extracted text content.
        source_path: Path to the source file (relative to project when possible).
        metadata: Optional key-value pairs with additional information.
    """

    entry_id: str
    entry_type: ExtractionEntryType
    text: str
    source_path: Path
    metadata: Mapping[str, str | int | float | bool | None] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class ExtractionResult:
    """Result of a data extraction operation.

    Attributes:
        status: The overall status of the extraction.
        entries: Tuple of successfully extracted entries.
        warnings: Non-blocking issues encountered during extraction.
        errors: Blocking issues that prevented full extraction.
        project: Optional reference to the source project.
    """

    status: ExtractionStatus
    entries: tuple[ExtractionEntry, ...] = ()
    warnings: tuple[ExtractionIssue, ...] = ()
    errors: tuple[ExtractionIssue, ...] = ()
    project: Project | None = None
