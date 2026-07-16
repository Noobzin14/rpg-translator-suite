# AGENTS.md

# RPG Translator Suite (RTS)

This document defines the permanent development rules for every AI agent and contributor working on RTS.

These rules take precedence over implementation preferences.

---

# Mission

Build a modular, extensible and maintainable localization platform for RPG Maker and similar game engines.

The software must prioritize architecture quality over implementation speed.

---

# Core Principles

- Keep the Core engine-independent.
- Prefer composition over inheritance when appropriate.
- Avoid code duplication.
- Keep modules loosely coupled.
- Write clean and readable code.
- Think long-term.

---

# Architecture Rules

## The Core

The Core must NEVER contain engine-specific logic.

Allowed:

Core → Plugin API → Plugins

Forbidden:

Core → RPG Maker MV

Core → RPG Maker XP

Core → Any engine implementation

---

# Plugin System

Every supported engine MUST be implemented as a plugin.

Never place engine logic outside `/plugins`.

---

# Development Strategy

Implement ONE feature at a time.

Never implement multiple unrelated systems in the same task.

Each implementation should remain small and reviewable.

---

# Coding Standards

Python 3.12+

Follow:

- PEP8
- Type hints
- Docstrings
- SOLID
- DRY
- KISS

Avoid premature optimization.

---

# Project Structure

Never change the directory structure without justification.

Respect:

app/

plugins/

docs/

tests/

resources/

---

# Dependencies

Prefer Python standard library whenever possible.

Only introduce third-party libraries when there is a clear benefit.

---

# GUI

Framework:

PySide6

The GUI must communicate only with the Core.

Never communicate directly with plugins.

---

# Database

SQLite

All database access must go through DatabaseManager.

Never execute SQL directly from GUI or plugins.

---

# Plugin Communication

Plugins communicate only through the Core.

Plugins must never call each other.

---

# Error Handling

Never silently ignore exceptions.

Errors must:

- be logged;
- provide meaningful messages;
- preserve project integrity.

---

# Logging

Use Python's logging module.

Never use print() for debugging in production code.

---

# Testing

Every new Core module should include unit tests whenever practical.

Avoid merging code that cannot be tested.

---

# Documentation

When implementing a feature:

- update documentation if necessary;
- keep comments concise;
- document public APIs.

---

# Security

Never overwrite original game files without creating a backup.

Never execute arbitrary scripts.

Never trust external project files without validation.

---

# Performance

Prioritize readability first.

Optimize only after measuring bottlenecks.

---

# AI Guidelines

If requirements are ambiguous:

STOP.

Explain the ambiguity.

Request clarification before implementing.

Never invent missing requirements.

---

# Pull Requests

Keep Pull Requests focused.

One feature.

One purpose.

Small changes.

---

# Forbidden

Do NOT:

- change project architecture without reason;
- introduce unnecessary dependencies;
- create circular imports;
- hardcode engine-specific behavior in the Core;
- bypass PluginManager.

---

# Expected Development Flow

Understand the documentation.

↓

Implement one feature.

↓

Run tests.

↓

Review.

↓

Document.

↓

Commit.

---

# Goal

RTS should become a professional, extensible localization platform capable of supporting multiple game engines without changing the Core architecture.
