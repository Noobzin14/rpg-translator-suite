# RPG Translator Suite (RTS)
## Roadmap

> **Version:** 0.2 (Planning)  
> **Status:** Active Development

---

# Vision

RPG Translator Suite (RTS) aims to become a professional, modular and extensible localization platform capable of supporting multiple game engines through a unified plugin architecture.

The project is developed incrementally, with each Sprint delivering a stable and reviewable milestone.

---

# Roadmap Status

| Status | Meaning |
|---------|---------|
| ⚪ Planned | Not started |
| 🟡 In Progress | Currently under development |
| 🟢 Completed | Finished |
| 🔴 Blocked | Waiting for dependency |

---

# Phase 1 — Foundation

Establish the technical foundation of RTS.

---

## Sprint 0.1 — Core Foundation

**Status:** 🟡 In Progress

### Goal

Build a clean and maintainable application foundation without implementing translation features.

### Tasks

- 🟢 Project structure
- 🟢 Python project configuration
- 🟢 `main.py`
- 🟢 Application bootstrap
- 🟢 ConfigManager
- 🟢 Logger
- 🟢 BasePlugin
- 🟢 PluginManager
- 🟢 MainWindow (minimal)
- 🟢 Initial unit tests

### Remaining

- ⚪ PluginRegistry
- ⚪ PluginLoader
- ⚪ PluginState
- ⚪ Event System
- ⚪ Exception hierarchy
- ⚪ Constants module
- ⚪ Version module
- ⚪ Improve BasePlugin (ABC)
- ⚪ Architectural review
- ⚪ Increase test coverage

### Deliverable

**Milestone**

```
v0.1.0-alpha
```

Capabilities:

- Application starts successfully.
- Core initializes.
- GUI opens.
- Plugins can be registered.
- Foundation ready for engine detection.

---

## Sprint 0.2 — Engine Detection

**Status:** ⚪ Planned

### Goal

Automatically identify supported game engines.

### Tasks

- Plugin discovery
- Plugin loading
- Engine detection pipeline
- Project validation
- Engine information screen

Supported engines:

- RPG Maker XP
- RPG Maker VX
- RPG Maker VX Ace
- RPG Maker MV
- RPG Maker MZ

### Deliverable

The application identifies the project engine and version without modifying any files.

---

## Sprint 0.3 — Project Loading

**Status:** ⚪ Planned

### Goal

Open projects safely.

### Tasks

- Project model
- Metadata loading
- File validation
- Read-only project loading
- Navigation tree

### Deliverable

Projects can be opened and inspected.

---

# Phase 2 — Translation Engine

Build the translation workflow.

---

## Sprint 0.4 — Text Extraction

**Status:** ⚪ Planned

### Tasks

- JSON extraction
- Maps
- Events
- Actors
- Classes
- Items
- Weapons
- Armors
- Skills
- Enemies
- Troops
- Common Events

### Deliverable

All translatable text is extracted.

---

## Sprint 0.5 — Database

**Status:** ⚪ Planned

### Tasks

- SQLite integration
- Translation database
- Project storage
- Translation Memory
- Glossary
- Search indexes

### Deliverable

Translation data is stored locally.

---

## Sprint 0.6 — Translation Editor

**Status:** ⚪ Planned

### Tasks

- Translation editor
- Search
- Replace
- Filters
- Context panel
- Autosave
- Progress tracking

### Deliverable

Users can translate projects through the editor.

---

## Sprint 0.7 — Validation

**Status:** ⚪ Planned

### Tasks

- Escape codes
- Variables
- JSON validation
- Overflow detection
- Missing translations
- Validation report

### Deliverable

Projects can be validated before export.

---

## Sprint 0.8 — Patch System

**Status:** ⚪ Planned

### Tasks

- Patch Builder
- Patch Installer
- Patch Verification
- Backup creation

### Deliverable

Translation patches can be generated and applied safely.

---

# Phase 3 — Community Edition

Release the first public version.

---

## Sprint 1.0

**Status:** ⚪ Planned

### Features

- Stable translation workflow
- Plugin support
- Translation Memory
- Glossary
- Validation
- Patch Builder
- Automatic updates
- Settings
- Theme support

### Deliverable

```
RTS Community 1.0
```

---

# Phase 4 — Studio Edition

Professional localization tools.

**Status:** ⚪ Planned

### Planned Features

- Full project export
- CLI
- REST API
- Team collaboration
- Cloud synchronization
- Enterprise licensing
- Build automation
- CI/CD integration

---

# Phase 5 — AI Integration

**Status:** ⚪ Planned

### Planned Features

- OpenAI
- Claude
- Gemini
- Ollama
- LM Studio
- Translation suggestions
- Context-aware translation
- Protected variable handling

---

# Phase 6 — Multi-Engine Expansion

**Status:** ⚪ Planned

### Planned Engines

### RPG Maker

- XP
- VX
- VX Ace
- MV
- MZ

### Visual Novel

- Ren'Py
- TyranoBuilder
- Visual Novel Maker

### RPG Engines

- Wolf RPG Editor
- SRPG Studio

### Future

- Godot localization
- Unity localization
- Unreal localization

---

# Long-Term Goals

- Universal plugin architecture
- Marketplace for plugins
- Collaborative translation
- Cloud projects
- OCR support
- Image localization
- Subtitle localization
- Voice localization
- Translation analytics
- Package manager
- Public SDK

---

# Release Strategy

| Version | Objective |
|----------|-----------|
| v0.1.0-alpha | Foundation |
| v0.2.0-alpha | Engine Detection |
| v0.3.0-alpha | Project Loading |
| v0.4.0-alpha | Text Extraction |
| v0.5.0-alpha | Database |
| v0.6.0-alpha | Translation Editor |
| v0.7.0-alpha | Validation |
| v0.8.0-alpha | Patch System |
| v1.0.0 | Community Edition |

---

# Development Principles

- One sprint at a time.
- One major feature per sprint.
- Core remains engine-independent.
- Every engine is implemented as a plugin.
- Documentation evolves alongside the code.
- Maintain high test coverage.
- Prefer maintainability over rapid feature growth.

---

# Current Sprint

🟡 **Sprint 0.1 — Core Foundation**

Current objective:

Finish the architectural foundation, review the implementation, strengthen the plugin infrastructure and prepare the project for engine detection in Sprint 0.2.
