# UI / UX Specification
## RPG Translator Suite (RTS)

Version: 0.1 (Draft)

---

# Purpose

This document defines the user interface, user experience, navigation flow and visual guidelines for RPG Translator Suite.

The goal is to create an interface that is intuitive for beginners while remaining powerful enough for professional localization teams.

---

# Design Principles

- Clean
- Fast
- Minimal
- Responsive
- Accessible
- Keyboard Friendly
- Cross-platform

---

# Design Language

Inspired by

- Visual Studio Code
- Qt Creator
- JetBrains IDEs
- Poedit
- GitHub Desktop

---

# Theme

Default

Dark

Optional

- Light
- High Contrast

---

# Main Window

```
+------------------------------------------------------------+
| Menu Bar                                                   |
+------------------------------------------------------------+
| Toolbar                                                    |
+------------------------------------------------------------+
| Explorer | Translation Editor | Context | Validation Panel |
|          |                    |         |                  |
|          |                    |         |                  |
+------------------------------------------------------------+
| Status Bar                                                 |
+------------------------------------------------------------+
```

---

# Navigation

Pages

```
Welcome

↓

Open Project

↓

Dashboard

↓

Translation Editor

↓

Validation

↓

Patch Builder

↓

Settings
```

---

# Welcome Screen

Buttons

- Open Project
- Recent Projects
- New Project
- Documentation
- About

---

# Dashboard

Displays

- Project Name
- Engine
- Engine Version
- Progress
- Translation Percentage
- Validation Status
- Recent Activity

---

# Project Explorer

Shows

```
Project

├── Actors
├── Classes
├── Items
├── Weapons
├── Armors
├── Skills
├── States
├── Enemies
├── Troops
├── Common Events
├── Maps
│   ├── Map001
│   ├── Map002
│   └── ...
└── Glossary
```

Supports

- Search
- Collapse
- Expand
- Favorites

---

# Translation Editor

Layout

```
Original

----------------------------------

Welcome to Aldlyn.

----------------------------------

Translation

----------------------------------

Bem-vindo a Aldlyn.
```

Additional Information

- Speaker
- File
- Map
- Event
- Context
- Character Limit

---

# Context Panel

Displays

- Event ID
- Map
- NPC
- Portrait
- Original Script
- Notes

Future

Mini Map Preview

---

# Search

Supports

- Exact
- Contains
- Regex
- Case Sensitive
- Fuzzy Search

---

# Filters

Show only

- Untranslated
- Reviewed
- Approved
- Locked
- With Notes
- By File
- By Speaker

---

# Glossary

Columns

```
Original

↓

Translation

↓

Category

↓

Description
```

Supports

- Lock Terms
- Import
- Export

---

# Translation Memory

Displays

Previous translations

Usage count

Confidence

Suggested translation

---

# Validation Window

Shows

✔ Errors

⚠ Warnings

ℹ Information

Clicking an error navigates directly to the affected entry.

---

# Patch Builder

Community Edition

```
Select Project

↓

Generate Patch

↓

Save .rtpatch
```

---

# Patch Installer

```
Select Game

↓

Select Patch

↓

Validate

↓

Apply
```

Progress bar included.

---

# Studio Edition

Additional Menus

- Export
- Build
- CLI
- API
- Team
- Cloud

---

# Toolbar

Buttons

- Open
- Save
- Undo
- Redo
- Search
- Validate
- Generate Patch
- Export
- Settings

---

# Status Bar

Displays

Project

Engine

Current File

Progress

Autosave

Errors

Warnings

AI Status

---

# Notifications

Types

- Success
- Warning
- Error
- Information

Never use intrusive pop-ups for minor events.

---

# Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl + O | Open Project |
| Ctrl + S | Save |
| Ctrl + F | Search |
| Ctrl + H | Replace |
| Ctrl + Z | Undo |
| Ctrl + Y | Redo |
| Ctrl + G | Go To Entry |
| F5 | Validate |
| F9 | Generate Patch |

---

# Accessibility

Supports

- Screen readers
- Keyboard navigation
- High contrast
- Scalable fonts
- Color-blind friendly indicators

---

# Icons

Use SVG icons.

Categories

- File
- Folder
- Engine
- Translation
- AI
- Database
- Warning
- Error
- Patch
- Export

---

# Loading

Long operations display

- Progress bar
- Current task
- Estimated time

GUI must remain responsive.

---

# Error Dialog

Displays

Problem

Possible Cause

Suggested Solution

Technical Details

Copy Log

---

# Future Features

- Visual Dialogue Editor
- Mini Map Preview
- Portrait Preview
- Image Localization
- Audio Localization
- Collaborative Editing
- AI Context Window

---

# UX Goals

The interface should allow a new user to:

1. Open a project.
2. Detect the engine automatically.
3. Extract texts.
4. Translate entries.
5. Validate the project.
6. Generate a translation patch.

without reading the documentation.

---

# Design Philosophy

The interface should prioritize simplicity while exposing advanced functionality progressively.

Beginner users should be able to translate a game within minutes.

Professional users should have access to advanced tools without cluttering the interface.