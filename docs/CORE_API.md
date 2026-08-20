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
