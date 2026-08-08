# Database Design
## RPG Translator Suite

Version: 0.1

---

# Overview

RTS stores all translation data inside a SQLite database.

This replaces spreadsheets and allows fast searching, filtering and versioning.

---

# Database

SQLite

Encoding

UTF-8

---

# Tables

Projects

Entries

Glossary

TranslationMemory

History

Comments

Review

Settings

Users (Studio)

---

# Projects

Stores project metadata.

Columns

```
id

name

engine

engine_version

path

language_source

language_target

created_at

updated_at
```

---

# Entries

Stores every translatable string.

Columns

```
id

project_id

file

map

event

page

command

speaker

context

original

translated

status

notes

created_at

updated_at
```

---

# Status

Possible values

```
NEW

TRANSLATED

REVIEW

APPROVED

LOCKED
```

---

# Glossary

Stores fixed terminology.

Columns

```
id

source

target

description

category

locked
```

---

# Translation Memory

Stores repeated translations.

Columns

```
id

source

target

usage_count

last_used
```

---

# History

Stores changes.

Columns

```
id

entry_id

user

old_value

new_value

timestamp
```

---

# Comments

Translator discussions.

Columns

```
id

entry_id

author

comment

created_at
```

---

# Review

Quality control.

Columns

```
id

entry_id

reviewer

approved

rating

notes
```

---

# Settings

Project configuration.

Columns

```
theme

autosave

language

ai_provider

font_size
```

---

# Studio Users

Future feature.

Columns

```
id

name

email

role

permissions
```

---

# Relationships

```
Projects

↓

Entries

↓

History

↓

Comments

↓

Review
```

---

# Indexes

Indexes

```
Entries.original

Entries.file

Entries.status

Glossary.source

TranslationMemory.source
```

---

# Search

Supports

Exact

Contains

Regex

Fuzzy

Case sensitive

Case insensitive

---

# Backup

Automatic before

Import

Patch generation

Export

Migration

---

# Migration

Database versions

```
1

2

3

...
```

Migration scripts

```
migrations/

001_initial.sql

002_add_review.sql

003_add_comments.sql
```

---

# Performance Goals

Project size

100,000+

entries

Search

<100ms

Project loading

<2s

Autosave

<1s

---

# Future

Planned support

Cloud sync

Multiple translators

Conflict resolution

Git integration

Translation statistics

Machine translation cache