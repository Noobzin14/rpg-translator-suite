# CORE API
## RPG Translator Suite (RTS)

Version: 0.1 (Draft)

---

# Purpose

The Core is the central component of RPG Translator Suite.

It coordinates every subsystem while remaining completely independent from any specific game engine.

The Core never reads or writes engine-specific files directly.

All engine operations are delegated to plugins.

---

# Core Responsibilities

The Core is responsible for:

- Project lifecycle
- Plugin management
- Translation workflow
- Event dispatching
- Database access
- Configuration
- Logging
- Autosave
- Validation orchestration
- Patch orchestration

The Core MUST NOT contain engine-specific logic.

---

# Core Architecture

```
                    GUI
                     │
                     │
              Core Controller
                     │
 ┌───────────────────┼────────────────────┐
 │                   │                    │
 │                   │                    │
Plugin Manager   Database Manager   Event Manager
 │                   │                    │
 │                   │                    │
Plugin API      SQLite Database      Event Bus
```

---

# Main Modules

```
core/

application.py

project_manager.py

plugin_manager.py

database_manager.py

event_manager.py

translation_manager.py

validation_manager.py

patch_manager.py

configuration.py

logger.py

exceptions.py
```

---

# Application Lifecycle

```
Application Start

↓

Load Settings

↓

Initialize Logger

↓

Initialize Event Manager

↓

Initialize Database

↓

Load Plugins

↓

Initialize GUI

↓

Ready
```

---

# Project Lifecycle

```
Open Project

↓

Detect Engine

↓

Load Plugin

↓

Read Metadata

↓

Extract Data

↓

Store Database

↓

Open Editor
```

---

# Translation Workflow

```
Open Entry

↓

Edit Translation

↓

Validate

↓

Autosave

↓

Update Translation Memory

---

# Project Loading API (Sprint 0.3, Stage 3)

Sprint 0.3 Stage 3 introduces `ProjectLoader` as the Core entry point for loading projects.
The Core remains engine-independent: it orchestrates detection, plugin resolution, and
generic filesystem validation.

## ProjectLoader

```python
class ProjectLoader:
    """Orchestrates project loading by coordinating detection and plugin structure APIs."""

    def __init__(
        self,
        detector: ProjectDetector,
        plugin_manager: PluginManager,
    ) -> None:
        """Initialize with detector and plugin manager."""

    def load(self, project_path: Path) -> ProjectLoadResult:
        """Load a project from the given path."""
```

## Load Flow

```
project_path
    ↓
Validate path (exists, is directory)
    ↓
ProjectDetector.detect()
    ↓
DetectionResult
    ↓
Handle detection status:
  - UNKNOWN → UNKNOWN_ENGINE
  - CONFLICT → ENGINE_CONFLICT
  - INCOMPLETE → INCOMPLETE
  - INVALID_PATH → INVALID_PATH
  - DETECTED → continue
    ↓
Resolve plugin via PluginManager.get(engine_id)
    ↓
plugin.describe_project_structure(project_path, detection)
    ↓
ProjectStructureSpec
    ↓
Generic filesystem validation:
  - Check path safety (no traversal, no absolute paths)
  - Check symlinks (don't follow outside project)
  - Check existence
  - Gather metadata (size, mtime)
    ↓
Build ProjectFile entries
    ↓
Build ProjectStructure
    ↓
Build Project
    ↓
ProjectLoadResult
```

## Detection Status Handling

| DetectionStatus | ProjectLoadStatus | Project | Notes |
|-----------------|-------------------|---------|-------|
| `DETECTED` | `LOADED` or `INCOMPLETE` | Yes | Depends on required files present |
| `UNKNOWN` | `UNKNOWN_ENGINE` | None | Issue: `unknown_engine` |
| `CONFLICT` | `ENGINE_CONFLICT` | None | Issue: `engine_conflict` |
| `INCOMPLETE` (no engine) | `INCOMPLETE` | None | Partial evidence only |
| `INCOMPLETE` (with engine) | `INCOMPLETE` | None | Engine known but project incomplete |
| `INVALID_PATH` | `INVALID_PATH` | None | Path doesn't exist or not a directory |

## ProjectLoadResult Fields

- `status`: `ProjectLoadStatus` indicating overall result
- `project`: `Project | None` - the loaded project if successful
- `warnings`: `tuple[ProjectIssue, ...]` - non-blocking issues
- `errors`: `tuple[ProjectIssue, ...]` - blocking issues
- `detection`: `DetectionResult | None` - preserved detection result

## Project Structure Validation

The Core validates `ProjectFileSpec` entries generically:

1. **Path Safety**: Rejects absolute paths and path traversal (`..`)
2. **Symlinks**: Does not follow symlinks outside project root
3. **Existence**: Checks if declared files/directories exist
4. **Metadata**: Gathers size and modification time via `stat()`
5. **No Content Reading**: Never opens file contents during loading

## Issue Codes

Common issue codes generated during loading:

- `invalid_path`: Path doesn't exist or is not a directory
- `unknown_engine`: No supported engine detected
- `engine_conflict`: Multiple engines detected
- `plugin_not_available`: Detected engine plugin not found
- `invalid_relative_path`: Spec contains unsafe path
- `symlink_outside_project`: Required symlink points outside project
- `symlink_skipped`: Optional symlink points outside project
- `missing_expected_file`: Required/optional file missing
- `missing_expected_directory`: Required/optional directory missing

## Status Determination

Project status is `LOADED` when all required files/directories are present.
Project status is `INCOMPLETE` when any required item is missing.

Optional items missing generate warnings but do not affect status.

---

# Translation Pipeline API (Sprint 0.4, Stage 2)

Sprint 0.4 Stage 2 introduces the Translation Pipeline API as the Core entry point for translating extracted text entries. The Core remains engine-independent: it orchestrates validation, calls translator implementations through an abstract interface, and returns structured results.

## TranslationEntry

```python
@dataclass(frozen=True)
class TranslationEntry:
    \"\"\"Represents a single text entry ready for translation.\"\"\"
    
    id: str                              # Stable identifier
    original_text: str                   # Text to translate (preserved exactly)
    context: str | None = None           # Optional context
    metadata: dict[...] = field(default_factory=dict)
    source_file: Path | None = None      # Optional source file path
    
    @classmethod
    def from_extraction_entry(cls, entry: ExtractionEntry) -> TranslationEntry:
        \"\"\"Create from an ExtractionEntry.\"\"\"
```

## Translator Interface

```python
class Translator(ABC):
    \"\"\"Abstract base class for translation engines.\"\"\"
    
    @property
    @abstractmethod
    def translator_id(self) -> str:
        \"\"\"Unique identifier (e.g., 'qwen', 'openai', 'manual').\"\"\"
    
    @abstractmethod
    def translate(self, entry: TranslationEntry) -> TranslationResult:
        \"\"\"Translate a single entry.\"\"\"
```

**Note:** Concrete translator implementations (QwenTranslator, OpenAITranslator, etc.) are NOT part of the Core. They belong in separate modules/plugins.

## TranslationResult

```python
@dataclass(frozen=True)
class TranslationResult:
    \"\"\"Result of translating a single entry.\"\"\"
    
    entry_id: str
    status: TranslationStatus
    original_text: str              # Preserved exactly as received
    translated_text: str | None     # None if not translated
    translator: str | None          # Translator identifier
    issues: tuple[TranslationIssue, ...]
```

## TranslationStatus

```python
class TranslationStatus(str, Enum):
    PENDING = "pending"         # Not processed yet
    TRANSLATED = "translated"   # Valid translation exists
    SKIPPED = "skipped"         # Deliberately ignored
    FAILED = "failed"           # Translation attempt failed
    INVALID = "invalid"         # Structurally invalid entry
```

## TranslationIssue

```python
@dataclass(frozen=True)
class TranslationIssue:
    \"\"\"Represents an issue found during translation.\"\"\"
    
    severity: TranslationIssueSeverity
    code: str                    # e.g., 'empty_source', 'translator_failed'
    message: str
    entry_id: str | None = None
    source_file: Path | None = None
```

## TranslationIssueSeverity

```python
class TranslationIssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
```

## TranslationBatchResult

```python
@dataclass(frozen=True)
class TranslationBatchResult:
    \"\"\"Aggregated result of translating multiple entries.\"\"\"
    
    results: tuple[TranslationResult, ...]
    issues: tuple[TranslationIssue, ...] = ()
```

## TranslationPipeline

```python
class TranslationPipeline:
    \"\"\"Orchestrates translation of multiple entries.\"\"\"
    
    def __init__(self, translator: Translator) -> None:
        \"\"\"Initialize with a translator implementation.\"\"\"
    
    def translate(
        self,
        entries: Sequence[TranslationEntry],
    ) -> TranslationBatchResult:
        \"\"\"Translate a batch of entries.\"\"\"
```

## Translation Flow

```
ExtractionResult
    ↓
TranslationEntry (from ExtractionEntry)
    ↓
TranslationPipeline
    ↓
Translator.translate()
    ↓
TranslationResult
    ↓
TranslationBatchResult
```

## Pipeline Behavior

- **Validation**: Entries with empty `id` or empty `original_text` are marked as `INVALID`
- **Error Isolation**: A failure in one entry does not stop processing of others
- **Exception Handling**: Translator exceptions are caught and converted to `FAILED` status with `translator_failed` issue
- **Text Preservation**: `original_text` is never modified (no trimming, normalization, or placeholder parsing)
- **Status Propagation**: `SKIPPED` and `FAILED` statuses from translators are preserved

## Issue Codes

Common issue codes generated during translation:

- `empty_source`: Original text is empty (WARNING severity)
- `invalid_entry`: Entry ID is empty or whitespace-only (ERROR severity)
- `translator_failed`: Translator raised an exception (ERROR severity)
- `translator_skipped`: Translator chose to skip the entry (INFO severity)

---

# Engine Detection API

Sprint 0.2 introduces `ProjectDetector` as the Core entry point for engine
detection. The Core remains engine-independent: it validates the candidate
directory, calls plugins through `PluginLoader`, and returns a structured
`DetectionResult`.

`DetectionResult` contains:

- `status`
- `engine`
- `display_name`
- `version`
- `project_path`
- `confidence`
- `evidence`
- `reason`
- `conflicts`

Possible statuses are `detected`, `unknown`, `conflict`, `invalid_path`, and
`incomplete`.

Status semantics:

- `detected`: exactly one plugin confirmed an engine through structured detection.
- `unknown`: no plugin found enough evidence for a supported engine.
- `incomplete`: at least one plugin found partial evidence, but no plugin
  confirmed a complete project.
- `conflict`: more than one plugin returned structured `detected` results.
- `invalid_path`: the candidate path does not exist or is not a directory.

Legacy boolean `detect()` matches are compatibility signals only. The default
adapter reports `True` as low-confidence `incomplete` with explicit legacy
evidence, so it cannot conflict with an evidence-backed structured detection.

The Core does not inspect RPG Maker-specific files directly. Those checks are
owned by engine plugins.

---

# Project Loading Models

Sprint 0.3 introduces engine-independent models for representing loaded projects.
These models are defined in `app.core.project_model` and include:

- `ProjectLoadStatus`: Status of a project loading operation.
- `ProjectIssueSeverity`: Severity levels for project issues.
- `ProjectIssue`: Represents an issue found during project loading.
- `ProjectFileKind`: Kinds of file system entries (file, directory, symlink, other).
- `ProjectFileRole`: Logical roles (root, config, data, script, asset, plugin, metadata, unknown).
- `ProjectFileSpec`: Specification for a file/directory in a project structure (used by plugins to describe expected structure).
- `ProjectStructureSpec`: Specification describing the expected/relevant structure of a project.
- `ProjectFile`: Represents a single file or directory entry.
- `ProjectStructure`: Represents the structure of a loaded project.
- `ProjectMetadata`: Engine-independent metadata container.
- `Project`: Represents a loaded project.
- `ProjectLoadResult`: Result of attempting to load a project.

## Plugin Structure API (Sprint 0.3)

Plugins can describe the expected structure of projects for their engine using `describe_project_structure()`:

```python
def describe_project_structure(
    self,
    project_path: Path,
    detection: DetectionResult,
) -> ProjectStructureSpec:
    \"\"\"Describe the expected/relevant structure for this engine's projects.\"\"\"
```

**Responsibilities:**

- **Plugin**: Describes engine-specific structure using generic models (`ProjectFileSpec`, `ProjectStructureSpec`).
- **Core**: Validates filesystem against the description and transforms it into `Project` (future sprint).

These models remain fully engine-independent. Engine-specific operations such as
reading files, scanning directories, or extracting metadata are deferred to
plugins and future sprints.
