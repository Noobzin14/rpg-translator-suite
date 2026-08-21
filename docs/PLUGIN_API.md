# Plugin API
## RPG Translator Suite

Version: 0.3

---

# Overview

Every supported engine is implemented as an independent plugin.

The Core never directly manipulates game files.

Instead, it delegates all engine-specific operations to the corresponding plugin.

Each plugin must implement the same interface.

---

# Plugin Lifecycle

```
Detect

↓

Load

↓

Extract

↓

Translate

↓

Validate

↓

Build

↓

Export
```

---

# Required Interface

Every plugin MUST inherit from `BasePlugin`.

```python
class BasePlugin:

    def metadata(self):
        pass

    def detect(self, path):
        pass

    def open_project(self, path):
        pass

    def extract(self):
        pass

    def import_translation(self):
        pass

    def validate(self):
        pass

    def build_patch(self):
        pass

    def export_project(self):
        pass
```

---

# Project Structure Description (Sprint 0.3)

Plugins can describe the expected/relevant structure of projects for their engine using engine-independent models. This allows the Core to understand project layouts without knowing engine-specific details.

## describe_project_structure()

```python
def describe_project_structure(
    self,
    project_path: Path,
    detection: DetectionResult,
) -> ProjectStructureSpec:
    \"\"\"Describe the expected/relevant structure for this engine's projects.

    Plugins may override this method to declare what files and directories
    they expect or consider relevant for a given engine.

    This method is NOT a project loader. It only describes the expected
    structure; it does not read files, scan directories, or extract data.
    \"\"\"
```

**Responsibilities:**

- **Plugin**: Describes engine-specific structure using generic models (`ProjectFileSpec`, `ProjectStructureSpec`).
- **Core**: Validates filesystem against the description and transforms it into `Project` (future sprint).

**Default Behavior:**

Plugins that do not override this method return an empty `ProjectStructureSpec`. This maintains compatibility and does not raise errors during normal flows.

---

# ProjectFileSpec

Describes a single file or directory in a project structure.

```python
@dataclass(frozen=True)
class ProjectFileSpec:
    relative_path: Path          # Path relative to project root
    kind: ProjectFileKind        # FILE, DIRECTORY, SYMLINK, OTHER
    role: ProjectFileRole        # ROOT, CONFIG, DATA, SCRIPT, ASSET, PLUGIN, METADATA, UNKNOWN
    required: bool = False       # Whether this entry is required
    description: str | None = None  # Optional human-readable description
```

**Example:**

```python
ProjectFileSpec(
    relative_path=Path("www/data/System.json"),
    kind=ProjectFileKind.FILE,
    role=ProjectFileRole.DATA,
    required=True,
    description="System data file containing game configuration.",
)
```

---

# ProjectStructureSpec

Describes the complete expected/relevant structure of a project.

```python
@dataclass(frozen=True)
class ProjectStructureSpec:
    metadata: Mapping[str, str | int | float | bool | None]
    expected_files: tuple[ProjectFileSpec, ...]
    expected_directories: tuple[ProjectFileSpec, ...]
    relevant_files: tuple[ProjectFileSpec, ...]
    relevant_directories: tuple[ProjectFileSpec, ...]
```

**Fields:**

- `metadata`: Engine-independent key-value pairs (e.g., `engine_family`, `runtime`).
- `expected_files`: Files that should exist for a valid project.
- `expected_directories`: Directories that should exist.
- `relevant_files`: Files that are useful but not required.
- `relevant_directories`: Directories that are useful but not required.

---

# Metadata

Example

```python
{
    "name": "RPG Maker MV",
    "engine": "mv",
    "version": "1.6.1",
    "author": "RTS Team",
    "supported": True
}
```

---

# Detect()

Purpose

Determines if the selected folder belongs to this engine.

Returns

```python
True
```

or

```python
False
```

Sprint 0.2 also supports the structured detection method:

```python
def detect_project(path) -> DetectionResult:
    pass
```

Plugins should return evidence-backed `DetectionResult` objects. Detection must
be read-only and must never execute scripts from the inspected project. Boolean
`detect()` remains available as a compatibility adapter only: if a plugin does
not override `detect_project()`, a legacy `detect()` result of `True` is reported
as low-confidence `incomplete` with explicit legacy evidence instead of
`detected`. This preserves the Sprint 0.1 method without treating an unevidenced
boolean as equivalent to structured engine confirmation.

---

# Open Project

Loads project metadata.

Returns

```python
ProjectInfo
```

Example

```
Project Name

Engine

Version

Root Folder

Data Folder

Plugin List
```

---

# Extract()

Extracts every translatable string.

Returns

```
TranslationEntry[]
```

---

# TranslationEntry

```python
class TranslationEntry:

    id

    file

    map

    event

    speaker

    original

    translated

    context

    notes
```

---

# Import Translation

Reads translated entries.

Updates internal structures.

Must never overwrite original files.

---

# Validate()

Returns

```
ValidationReport
```

Checks

- Missing translations

- Broken variables

- Escape codes

- JSON

- Event integrity

- Overflow

---

# Build Patch

Community Edition only.

Creates

```
.rtpatch
```

Must never include copyrighted assets.

---

# Export Project

Studio Edition only.

Generates a localized game project.

---

# Events

Plugins may emit events.

Example

```
ProjectOpened

ExtractionStarted

ExtractionFinished

ValidationFinished

PatchCreated

ExportFinished
```

---

# Error Handling

Plugins must never crash the Core.

Errors are reported as

```python
PluginError
```

---

# Capabilities

Each plugin declares supported features.

Example

```python
{
    "patch": True,
    "export": True,
    "validation": True,
    "ai": True
}
```

---

# Plugin Directory

```
plugins/

rpgmaker_mv/

plugin.py

manifest.json

icon.png

README.md
```

---

# Manifest

Example

```json
{
    "name": "RPG Maker MV",
    "engine": "mv",
    "version": "1.0",
    "author": "RTS Team",
    "api": "1.0"
}
```

---

# Plugin Compatibility

The Core loads plugins only if

Plugin API version == Core API version

Otherwise the plugin is ignored.

---

# Future Extensions

Future plugins may support

- Voice extraction
- Texture localization
- Font replacement
- Image OCR
- Subtitle synchronization

without changing the Core.