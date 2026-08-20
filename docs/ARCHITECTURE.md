# RPG Translator Suite (RTS)
## Software Architecture

> Version: 0.1 (Draft)

---

# Overview

RPG Translator Suite (RTS) is a modular localization platform designed to support multiple game engines through a plugin-based architecture.

The project is divided into independent modules that communicate through well-defined interfaces.

The Core must never depend on a specific game engine.

Instead, every engine implements the same Plugin API.

---

# Design Principles

- Modular Architecture
- Plugin-first development
- Engine independent Core
- Cross-platform
- Extensible
- Maintainable
- Testable
- Open-source friendly

---

# High-Level Architecture

```
                    +----------------------+
                    |        GUI           |
                    +----------+-----------+
                               |
                               |
                    +----------v-----------+
                    |        CORE          |
                    +----------+-----------+
                               |
        +----------------------+----------------------+
        |                      |                      |
        |                      |                      |
+-------v-------+      +-------v-------+      +-------v-------+
| Translation   |      | Database      |      | Validation    |
+---------------+      +---------------+      +---------------+
        |
        |
+-------v---------------------------------------------+
|                Plugin Manager                       |
+-------+----------------------+----------------------+
        |                      |                      |
        |                      |                      |
+-------v------+      +--------v------+      +--------v------+
| RPG Maker XP |      | RPG Maker MV  |      | RPG Maker MZ  |
+--------------+      +---------------+      +---------------+
```

---

# Directory Structure

```
rpg-translator-suite/

app/
│
├── core/
├── gui/
├── database/
├── translation/
├── validation/
├── patcher/
├── licensing/
├── updater/
└── plugin_manager/

plugins/
│
├── rpgmaker_xp/
├── rpgmaker_vx/
├── rpgmaker_vxace/
├── rpgmaker_mv/
├── rpgmaker_mz/
├── renpy/
├── wolf_rpg/
└── template/

docs/

tests/

examples/

resources/
```

---

# Core Responsibilities

The Core is responsible for:

- Project management
- Plugin loading
- Translation workflow
- Configuration
- Logging
- Settings
- Event dispatching

The Core MUST NOT contain engine-specific code.

---

# Plugin System

Every supported engine must implement the same interface. Engine detection is
confirmed only by structured plugin results; legacy boolean detection is treated
as partial, low-confidence compatibility evidence and cannot create a conflict
against a structured detector.

Example:

```python
class EnginePlugin:

    def detect(self):

    def extract(self):

    def import_translation(self):

    def validate(self):

    def build_patch(self):

    def apply_patch(self):
```

---

# Translation Pipeline

```
Game Project

↓

Detect Engine

↓

Load Plugin

↓

Extract Text

↓

SQLite Database

↓

Translation Editor

↓

Validation

↓

Patch Builder

↓

Distribution
```

---

# Translation Database

SQLite

Main tables

Projects

Entries

Glossary

Translation Memory

Metadata

History

Comments

Review

---

# Translation Entry

Each entry contains:

ID

Engine

File

Map

Event

Speaker

Original Text

Translated Text

Status

Context

Notes

Timestamp

---

# Plugin Responsibilities

Each plugin must provide:

Engine detection

Extraction

Import

Validation

Patch generation

Version detection

Capabilities

---

# Engine Detection

The Core orchestrates detection but does not contain engine-specific rules.

Sprint 0.2 detection flow:

```
ProjectDetector
↓
PluginLoader
↓
Engine detection plugins
↓
DetectionResult
```

`ProjectDetector` validates the selected folder, asks loaded plugins to inspect
the project in read-only mode, and consolidates the result. Engine-specific
evidence, such as RPG Maker MV runtime files, belongs inside the relevant plugin
under `plugins/`.

Detection can explicitly return detected, unknown, invalid path, incomplete, or
conflict states. Conflicts preserve the competing plugin results instead of
choosing silently.

Each plugin decides if it supports it.

Example

```
www/js/rpg_core.js

↓

RPG Maker MV 1.6.1
```

---

# Validation Layer

Responsible for:

JSON validation

Variables

Escape characters

Commands

Encoding

Broken references

Text overflow

---

# Translation Memory

Repeated strings are automatically suggested.

Example

Potion

↓

Poção

Future occurrences receive automatic suggestions.

---

# Glossary

Project-specific terminology.

Example

Quest

↓

Missão

---

Dragonic

↓

Dracônico

---

Skill

↓

Habilidade

---

# AI Layer

Optional.

Supported providers

OpenAI

Gemini

Claude

Ollama

LM Studio

The AI layer must preserve:

Variables

Escape codes

Control codes

Formatting

---

# Community Edition

Capabilities

✔ Translation

✔ Validation

✔ Patch generation

✔ Patch installer

Restrictions

✖ Full project export

---

# Studio Edition

Additional capabilities

Full export

CLI

REST API

CI/CD

Cloud

Team management

Automation

---

# Patch System

Community Edition distributes only patches.

Pipeline

```
Original Project

↓

Compare

↓

Generate .rtpatch

↓

Distribute
```

Users apply:

```
Original Game

+

Patch

↓

Localized Game
```

---

# Event System

Every module communicates through events.

Examples

ProjectOpened

PluginLoaded

ExtractionFinished

ValidationFinished

PatchGenerated

TranslationSaved

---

# Error Handling

All errors are logged.

Fatal errors never corrupt the project.

Automatic backup before:

Import

Patch generation

Database migration

---

# Future Architecture

Future modules

Voice Localization

Subtitle Synchronization

Visual Dialogue Editor

Cloud Translation

Collaborative Translation

Marketplace

---

# Coding Standards

Python 3.12+

PEP8

Type hints

Docstrings

Unit tests

No engine-specific code inside Core

---

# Long-Term Vision

RTS aims to become a universal localization platform capable of supporting dozens of game engines through independent plugins while keeping the Core clean, modular and maintainable.
