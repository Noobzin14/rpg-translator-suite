# Plugin API
## RPG Translator Suite

Version: 0.1

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