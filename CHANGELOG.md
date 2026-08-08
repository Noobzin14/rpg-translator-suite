# Changelog

All notable changes to this project will be documented in this file.

The format follows the principles of **Keep a Changelog** and **Semantic Versioning (SemVer)**.

---

## [Unreleased]

### Added

- Ongoing improvements under the current sprint.
- Internal architectural refinements.
- Documentation updates.
- Unit tests.
- Plugin infrastructure improvements.

---

# Version History

## [0.1.0-alpha] - 2026-08-08

### Added

#### Project Foundation

- Initial project structure.
- Python 3.12+ support.
- PySide6 application bootstrap.
- Project entry point (`main.py`).
- Initial package configuration.
- Requirements management.

#### Core

- Core application foundation.
- Application bootstrap layer.
- ConfigManager.
- Logger.
- RTS exception hierarchy.
- Centralized application versioning.

#### GUI

- Initial PySide6 GUI.
- Initial Main Window.
- "Open Project" home screen.

#### Plugins

- Plugin namespace.
- BasePlugin.
- PluginRegistry.
- PluginManager.
- PluginLoader foundation.
- PluginState.
- Plugin registration.
- Plugin validation.
- Duplicate plugin protection.

#### Testing

- Initial unit tests.
- ConfigManager tests.
- PluginManager tests.
- PluginRegistry tests.
- PluginLoader tests.

#### Validation

- `pytest -q`: 9 passed.
- `python -m compileall app tests`: passed.
- Core imports verified successfully.

#### Documentation

- README.md
- ROADMAP.md
- docs/ARCHITECTURE.md
- CONTRIBUTING.md
- AGENTS.md
- docs/CORE_API.md
- docs/DATABASE.md
- docs/PLUGIN_API.md
- docs/UI_UX.md

### Changed

- Sprint 0.1 marked as completed.
- Roadmap reorganized into Phases and Sprints.
- Foundation architecture refined after technical review.

### Fixed

- Initial architectural inconsistencies discovered during planning.

---

## [0.2.0-alpha] - Planned

### Planned

#### Engine Detection

- Plugin discovery.
- Plugin loading.
- RPG Maker detection.
- Engine version detection.
- Project validation.

Supported engines:

- RPG Maker XP
- RPG Maker VX
- RPG Maker VX Ace
- RPG Maker MV
- RPG Maker MZ

---

## [0.3.0-alpha] - Planned

### Planned

#### Project Reader

- Read-only project loading.
- Metadata parsing.
- Navigation tree.
- Project model.

---

## [0.4.0-alpha] - Planned

### Planned

#### Text Extraction

- JSON extraction.
- Maps.
- Events.
- Actors.
- Classes.
- Items.
- Weapons.
- Armors.
- Skills.
- Enemies.
- Troops.
- Common Events.

---

## [0.5.0-alpha] - Planned

### Planned

#### Database

- SQLite integration.
- Translation database.
- Translation Memory.
- Glossary.
- Search indexing.

---

## [0.6.0-alpha] - Planned

### Planned

#### Translation Editor

- Translation editor.
- Search.
- Replace.
- Filters.
- Autosave.
- Progress tracking.

---

## [0.7.0-alpha] - Planned

### Planned

#### Validation

- Escape code validation.
- Variable validation.
- JSON validation.
- Overflow detection.
- Missing translation detection.
- Validation reports.

---

## [0.8.0-alpha] - Planned

### Planned

#### Patch System

- Patch Builder.
- Patch Installer.
- Patch verification.
- Automatic backups.

---

## [1.0.0] - Planned

### Planned

#### RTS Community Edition

- Stable translation workflow.
- Plugin ecosystem.
- Translation Memory.
- Glossary.
- Validation.
- Patch generation.
- Automatic updates.
- Settings.
- Theme support.

---

## [2.0.0] - Planned

### Planned

#### RTS Studio Edition

- Full project export.
- CLI.
- REST API.
- Team collaboration.
- Cloud synchronization.
- Enterprise features.
- CI/CD integration.

---

## Future

### AI

- OpenAI
- Claude
- Gemini
- Ollama
- LM Studio

### New Engines

- Ren'Py
- Wolf RPG Editor
- TyranoBuilder
- Visual Novel Maker
- SRPG Studio

### Future Features

- OCR
- Image localization
- Voice localization
- Subtitle localization
- Cloud collaboration
- Plugin Marketplace
- Translation Analytics