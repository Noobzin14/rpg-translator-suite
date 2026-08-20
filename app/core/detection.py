"""Engine detection models for RPG Translator Suite."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ConfidenceLevel(str, Enum):
    """Supported confidence levels for engine detection."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DetectionStatus(str, Enum):
    """Possible outcomes of an engine detection attempt."""

    DETECTED = "detected"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"
    INVALID_PATH = "invalid_path"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class DetectionEvidence:
    """A single read-only fact used to identify an engine."""

    path: Path
    description: str
    confidence_weight: int = 1


@dataclass(frozen=True)
class DetectionResult:
    """Structured result produced by engine detection plugins and the Core."""

    status: DetectionStatus
    project_path: Path
    engine: str | None = None
    display_name: str | None = None
    version: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.NONE
    evidence: tuple[DetectionEvidence, ...] = ()
    reason: str | None = None
    conflicts: tuple["DetectionResult", ...] = field(default_factory=tuple)

    @property
    def detected(self) -> bool:
        """Return whether the result identifies an engine."""
        return self.status == DetectionStatus.DETECTED
