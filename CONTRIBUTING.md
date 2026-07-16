# Contributing to RPG Translator Suite (RTS)

First of all, thank you for your interest in contributing to RPG Translator Suite!

Our goal is to build a modern, modular and extensible localization platform for RPG Maker and similar game engines.

Please read this document before opening an Issue or Pull Request.

---

# Code of Conduct

Be respectful.

Constructive discussions are always welcome.

Harassment, offensive language or disruptive behavior will not be tolerated.

---

# Development Philosophy

RTS follows a modular architecture.

Core components must remain independent from engine-specific implementations.

Engine support must always be implemented through plugins.

---

# Before Contributing

Please:

- Search existing Issues.
- Search existing Pull Requests.
- Read the documentation inside `docs/`.
- Open an Issue before implementing large features.

---

# Project Structure

```
app/
plugins/
docs/
tests/
resources/
examples/
```

Engine-specific code belongs only inside `plugins/`.

---

# Coding Standards

- Python 3.12+
- Follow PEP 8
- Use type hints
- Use descriptive names
- Keep functions small
- Avoid duplicated code
- Write clear docstrings

---

# Documentation

Every significant feature must include documentation updates.

If you modify:

- Core
- Plugin API
- Database
- UI

please update the corresponding document inside `docs/`.

---

# Branch Naming

Use the following pattern:

```
feature/engine-detector
feature/plugin-mv
feature/sqlite

bugfix/json-parser

docs/readme

refactor/plugin-manager
```

---

# Commit Messages

Recommended format:

```
feat: add engine detector

fix: resolve JSON parser issue

docs: update architecture

refactor: simplify plugin loader

test: add validation tests
```

---

# Pull Requests

Each Pull Request should:

- Solve one problem.
- Be focused.
- Include documentation when necessary.
- Pass all tests.

Large Pull Requests may be requested to be split into smaller ones.

---

# Testing

Before submitting:

- Run all tests.
- Verify formatting.
- Check that no existing functionality is broken.

---

# Engine Plugins

Every plugin must implement the Plugin API.

Plugins should never communicate directly with other plugins.

---

# Bug Reports

Please include:

- RTS version
- Operating system
- Python version
- Engine
- Steps to reproduce
- Expected behavior
- Actual behavior
- Logs (if available)

---

# Feature Requests

Describe:

- The problem
- Proposed solution
- Alternative solutions
- Expected benefits

---

# Design Rules

The Core must never contain engine-specific logic.

GUI must never directly communicate with plugins.

Database access should always go through the Database Manager.

---

# Community Edition

Community Edition is intended for fan translators and localization teams.

Whenever possible, distribute translation patches instead of copyrighted game assets.

---

# Studio Edition

Commercial features are developed separately but share the same Core architecture.

---

# Maintainer Review

All Pull Requests are reviewed by the project maintainer.

Submitting a Pull Request does not guarantee acceptance.

Maintainers may request:

- changes
- improvements
- refactoring
- additional tests
- documentation updates

before merging.

---

# License

By contributing to RTS, you agree that your contribution will be distributed under the project's license (MPL 2.0 unless otherwise specified).

---

# Thank You

Every contribution, whether code, documentation, testing or bug reports, helps make RTS a better tool for the entire localization community.