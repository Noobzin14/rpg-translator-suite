"""Engine-independent project models for RPG Translator Suite."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping

from app.core.detection import DetectionResult


class ProjectLoadStatus(str, Enum):
    """Possible statuses for a loaded project."""

    LOADED = "loaded"
    INCOMPLETE = "incomplete"
    NOT_LOADED = "not_loaded"
    INVALID_PATH = "invalid_path"
    UNKNOWN_ENGINE = "unknown_engine"
    ENGINE_CONFLICT = "engine_conflict"
    ACCESS_ERROR = "access_error"
    READ_ERROR = "read_error"


class ProjectIssueSeverity(str, Enum):
    """Severity levels for project issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ProjectIssue:
    """Represents an issue found during project loading or validation."""

    severity: ProjectIssueSeverity
    code: str
    message: str
    path: Path | None = None


class ProjectFileKind(str, Enum):
    """Kinds of file system entries in a project."""

    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    OTHER = "other"


class ProjectFileRole(str, Enum):
    """Logical roles that files/directories may have in a project."""

    ROOT = "root"
    CONFIG = "config"
    DATA = "data"
    SCRIPT = "script"
    ASSET = "asset"
    PLUGIN = "plugin"
    METADATA = "metadata"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProjectFile:
    """Represents a single file or directory entry in a project."""

    path: Path
    relative_path: Path
    kind: ProjectFileKind
    role: ProjectFileRole
    size: int | None = None
    modified_at: float | None = None
    is_required: bool = False
    is_present: bool = True


@dataclass(frozen=True)
class ProjectStructure:
    """Represents the structure of a loaded project."""

    root: Path
    entries: tuple[ProjectFile, ...] = field(default_factory=tuple)
    relevant_files: tuple[Path, ...] = field(default_factory=tuple)
    relevant_directories: tuple[Path, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProjectMetadata:
    """Engine-independent project metadata.

    Values are limited to simple scalar types to remain engine-agnostic.
    Complex or engine-specific structures belong in plugins.
    """

    values: Mapping[str, str | int | float | bool | None] = field(default_factory=dict)

    def get(self, key: str, default: str | int | float | bool | None = None) -> str | int | float | bool | None:
        """Get a metadata value by key."""
        return self.values.get(key, default)

    def __getitem__(self, key: str) -> str | int | float | bool | None:
        """Get a metadata value by key using indexing."""
        return self.values[key]

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in metadata."""
        return key in self.values

    def __len__(self) -> int:
        """Return the number of metadata entries."""
        return len(self.values)


@dataclass(frozen=True)
class Project:
    """Represents a loaded project in an engine-independent manner."""

    path: Path
    engine: str | None = None
    engine_display_name: str | None = None
    engine_version: str | None = None
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    structure: ProjectStructure | None = None
    files: tuple[ProjectFile, ...] = field(default_factory=tuple)
    status: ProjectLoadStatus = ProjectLoadStatus.NOT_LOADED
    issues: tuple[ProjectIssue, ...] = field(default_factory=tuple)
    detection: DetectionResult | None = None


@dataclass(frozen=True)
class ProjectLoadResult:
    """Result of attempting to load a project."""

    status: ProjectLoadStatus
    project: Project | None = None
    warnings: tuple[ProjectIssue, ...] = field(default_factory=tuple)
    errors: tuple[ProjectIssue, ...] = field(default_factory=tuple)
    detection: DetectionResult | None = None
