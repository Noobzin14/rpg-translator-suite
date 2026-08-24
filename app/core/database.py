"""SQLite Database Manager for RPG Translator Suite.

This module provides a concrete SQLite implementation for persisting
translation data, following the schema defined in docs/DATABASE.md.

The database layer is designed to be:
- Engine-independent (no game engine specifics)
- Transaction-safe (ACID compliance)
- Unicode-safe (UTF-8 encoding)
- Thread-safe (connection per thread)
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.core.extraction import ExtractionEntryType
from app.core.translation import TranslationStatus


@dataclass(frozen=True)
class TranslationEntryRecord:
    """Record representation of a translation entry in the database.

    Attributes:
        id: Database row ID.
        project_id: Foreign key to the projects table.
        file: Source file path (relative).
        map: Map identifier (if applicable).
        event: Event identifier (if applicable).
        page: Page number (if applicable).
        command: Command identifier (if applicable).
        speaker: Speaker name (if applicable).
        context: Additional context information.
        original: Original text content.
        translated: Translated text content (may be empty).
        status: Translation status.
        notes: Optional notes.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: int
    project_id: int
    file: str | None
    map: str | None
    event: str | None
    page: str | None
    command: str | None
    speaker: str | None
    context: str | None
    original: str
    translated: str | None
    status: str
    notes: str | None
    created_at: str
    updated_at: str


class DatabaseManager:
    """SQLite database manager for translation data persistence.

    This class handles:
    - Database connection and lifecycle
    - Schema creation and migration
    - CRUD operations for translation entries
    - Transaction management (commit/rollback)
    - Query operations (by ID, by text, by original)
    - Unicode-safe storage (UTF-8)

    The database schema follows docs/DATABASE.md with tables for:
    - projects: Project metadata
    - entries: Translation entries
    - glossary: Fixed terminology (structure only, not implemented)
    - translation_memory: Repeated translations (structure only, not implemented)
    """

    # Schema version for future migrations
    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path | str) -> None:
        """Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file. If the file does not
                exist, it will be created automatically.

        Raises:
            ValueError: If db_path is empty.
            OSError: If the directory cannot be created or accessed.
        """
        if not db_path:
            raise ValueError("Database path cannot be empty")

        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._in_transaction = False

        # Ensure parent directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._initialize_database()

    def _should_auto_commit(self) -> bool:
        """Check if we should auto-commit (not inside a transaction)."""
        return not self._in_transaction

    def _initialize_database(self) -> None:
        """Initialize the database connection and create schema."""
        self._connect()
        try:
            self._create_schema()
        except Exception:
            self._close()
            raise

    def _connect(self) -> None:
        """Establish database connection."""
        if self._conn is not None:
            return

        self._conn = sqlite3.connect(
            str(self._db_path),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            isolation_level="DEFERRED",  # Enable transaction management
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA encoding = 'UTF-8'")

    def _close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass  # Ignore close errors
            finally:
                self._conn = None

    def close(self) -> None:
        """Public method to close the database connection.

        This should be called when the database manager is no longer needed.
        """
        self._close()

    def __enter__(self) -> DatabaseManager:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - ensures connection is closed."""
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Context manager for transaction handling.

        Usage:
            with db.transaction():
                db.insert_entry(...)
                db.update_entry(...)

        If an exception occurs within the block, the transaction is rolled back.
        Otherwise, it is committed.

        Yields:
            None

        Raises:
            DatabaseError: If a database error occurs during commit/rollback.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        conn = self._conn
        
        # Mark that we are inside a transaction (disable auto-commit)
        old_in_transaction = self._in_transaction
        self._in_transaction = True
        
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._in_transaction = old_in_transaction

    def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        cursor = self._conn.cursor()

        # Create projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                engine TEXT NOT NULL,
                engine_version TEXT,
                path TEXT NOT NULL UNIQUE,
                language_source TEXT,
                language_target TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Create entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                file TEXT,
                map TEXT,
                event TEXT,
                page TEXT,
                command TEXT,
                speaker TEXT,
                context TEXT,
                original TEXT NOT NULL,
                translated TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Create glossary table (structure only - functionality for future phases)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS glossary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL UNIQUE,
                target TEXT NOT NULL,
                description TEXT,
                category TEXT,
                locked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Create translation_memory table (structure only - functionality for future phases)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                usage_count INTEGER NOT NULL DEFAULT 1,
                last_used TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(source, target)
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_project_id
            ON entries(project_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_original
            ON entries(original)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_file
            ON entries(file)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_status
            ON entries(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_glossary_source
            ON glossary(source)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_translation_memory_source
            ON translation_memory(source)
        """)

        # Create schema version table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL PRIMARY KEY
            )
        """)

        # Insert schema version
        cursor.execute("""
            INSERT OR IGNORE INTO schema_version (version) VALUES (?)
        """, (self.SCHEMA_VERSION,))

        self._conn.commit()

    # =========================================================================
    # Project CRUD Operations
    # =========================================================================

    def create_project(
        self,
        name: str,
        engine: str,
        path: str,
        engine_version: str | None = None,
        language_source: str | None = None,
        language_target: str | None = None,
    ) -> int:
        """Create a new project record.

        Args:
            name: Project name.
            engine: Engine identifier (e.g., 'rpgmaker_mv').
            path: Absolute path to the project.
            engine_version: Engine version string.
            language_source: Source language code.
            language_target: Target language code.

        Returns:
            The ID of the newly created project.

        Raises:
            IntegrityError: If a project with the same path already exists.
            DatabaseError: If a database error occurs.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        now = datetime.now(timezone.utc).isoformat()

        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO projects
            (name, engine, engine_version, path, language_source, language_target, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, engine, engine_version, path, language_source, language_target, now, now))

        if self._should_auto_commit():
            self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_project(self, project_id: int) -> dict[str, Any] | None:
        """Get a project by ID.

        Args:
            project_id: The project ID.

        Returns:
            A dictionary with project data, or None if not found.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    def get_project_by_path(self, path: str) -> dict[str, Any] | None:
        """Get a project by path.

        Args:
            path: The project path.

        Returns:
            A dictionary with project data, or None if not found.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE path = ?", (path,))
        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    def update_project(
        self,
        project_id: int,
        **kwargs: Any,
    ) -> bool:
        """Update a project's fields.

        Args:
            project_id: The project ID.
            **kwargs: Fields to update (name, engine, engine_version, etc.).

        Returns:
            True if the project was updated, False if not found.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        allowed_fields = {
            "name", "engine", "engine_version", "path",
            "language_source", "language_target"
        }

        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)

        if not updates:
            return False

        now = datetime.now(timezone.utc).isoformat()
        updates.append("updated_at = ?")
        values.append(now)
        values.append(project_id)

        cursor = self._conn.cursor()
        cursor.execute(f"""
            UPDATE projects
            SET {", ".join(updates)}
            WHERE id = ?
        """, tuple(values))

        if self._should_auto_commit():
            self._conn.commit()
        return cursor.rowcount > 0

    def delete_project(self, project_id: int) -> bool:
        """Delete a project and all its entries.

        Args:
            project_id: The project ID.

        Returns:
            True if the project was deleted, False if not found.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        if self._should_auto_commit():
            self._conn.commit()
        return cursor.rowcount > 0

    # =========================================================================
    # Entry CRUD Operations
    # =========================================================================

    def insert_entry(
        self,
        project_id: int,
        original: str,
        file: str | None = None,
        map: str | None = None,
        event: str | None = None,
        page: str | None = None,
        command: str | None = None,
        speaker: str | None = None,
        context: str | None = None,
        status: str = TranslationStatus.PENDING.value,
        notes: str | None = None,
    ) -> int:
        """Insert a new translation entry.

        Args:
            project_id: Foreign key to the project.
            original: Original text content.
            file: Source file path (relative).
            map: Map identifier.
            event: Event identifier.
            page: Page number.
            command: Command identifier.
            speaker: Speaker name.
            context: Additional context.
            status: Translation status (default: 'pending').
            notes: Optional notes.

        Returns:
            The ID of the newly created entry.

        Raises:
            DatabaseError: If a database error occurs.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        now = datetime.now(timezone.utc).isoformat()

        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO entries
            (project_id, file, map, event, page, command, speaker, context,
             original, translated, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id, file, map, event, page, command, speaker, context,
            original, None, status, notes, now, now
        ))

        if self._should_auto_commit():
            self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_entry(self, entry_id: int) -> TranslationEntryRecord | None:
        """Get an entry by ID.

        Args:
            entry_id: The entry ID.

        Returns:
            A TranslationEntryRecord, or None if not found.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return TranslationEntryRecord(
            id=row["id"],
            project_id=row["project_id"],
            file=row["file"],
            map=row["map"],
            event=row["event"],
            page=row["page"],
            command=row["command"],
            speaker=row["speaker"],
            context=row["context"],
            original=row["original"],
            translated=row["translated"],
            status=row["status"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_entries_by_project(self, project_id: int) -> list[TranslationEntryRecord]:
        """Get all entries for a project.

        Args:
            project_id: The project ID.

        Returns:
            A list of TranslationEntryRecord objects.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM entries WHERE project_id = ? ORDER BY id",
            (project_id,)
        )

        return [
            TranslationEntryRecord(
                id=row["id"],
                project_id=row["project_id"],
                file=row["file"],
                map=row["map"],
                event=row["event"],
                page=row["page"],
                command=row["command"],
                speaker=row["speaker"],
                context=row["context"],
                original=row["original"],
                translated=row["translated"],
                status=row["status"],
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in cursor.fetchall()
        ]

    def get_entries_by_original(self, original: str) -> list[TranslationEntryRecord]:
        """Get entries by original text (exact match).

        Args:
            original: The original text to search for.

        Returns:
            A list of matching TranslationEntryRecord objects.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM entries WHERE original = ?",
            (original,)
        )

        return [
            TranslationEntryRecord(
                id=row["id"],
                project_id=row["project_id"],
                file=row["file"],
                map=row["map"],
                event=row["event"],
                page=row["page"],
                command=row["command"],
                speaker=row["speaker"],
                context=row["context"],
                original=row["original"],
                translated=row["translated"],
                status=row["status"],
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in cursor.fetchall()
        ]

    def get_entries_containing_text(
        self,
        text: str,
        in_original: bool = True,
        in_translated: bool = False,
    ) -> list[TranslationEntryRecord]:
        """Get entries containing text (partial match).

        Args:
            text: The text to search for.
            in_original: Search in original text.
            in_translated: Search in translated text.

        Returns:
            A list of matching TranslationEntryRecord objects.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        conditions = []
        params: list[Any] = []

        if in_original:
            conditions.append("original LIKE ?")
            params.append(f"%{text}%")

        if in_translated:
            conditions.append("translated LIKE ?")
            params.append(f"%{text}%")

        if not conditions:
            return []

        query = f"SELECT * FROM entries WHERE {' OR '.join(conditions)}"
        cursor = self._conn.cursor()
        cursor.execute(query, params)

        return [
            TranslationEntryRecord(
                id=row["id"],
                project_id=row["project_id"],
                file=row["file"],
                map=row["map"],
                event=row["event"],
                page=row["page"],
                command=row["command"],
                speaker=row["speaker"],
                context=row["context"],
                original=row["original"],
                translated=row["translated"],
                status=row["status"],
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in cursor.fetchall()
        ]

    def update_entry_translation(
        self,
        entry_id: int,
        translated: str,
        status: str = TranslationStatus.TRANSLATED.value,
    ) -> bool:
        """Update an entry's translation.

        Args:
            entry_id: The entry ID.
            translated: The translated text.
            status: The new status (default: 'translated').

        Returns:
            True if the entry was updated, False if not found.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        now = datetime.now(timezone.utc).isoformat()

        cursor = self._conn.cursor()
        cursor.execute("""
            UPDATE entries
            SET translated = ?, status = ?, updated_at = ?
            WHERE id = ?
        """, (translated, status, now, entry_id))

        if self._should_auto_commit():
            self._conn.commit()
        return cursor.rowcount > 0

    def update_entry_status(
        self,
        entry_id: int,
        status: str,
    ) -> bool:
        """Update an entry's status.

        Args:
            entry_id: The entry ID.
            status: The new status.

        Returns:
            True if the entry was updated, False if not found.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        now = datetime.now(timezone.utc).isoformat()

        cursor = self._conn.cursor()
        cursor.execute("""
            UPDATE entries
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, (status, now, entry_id))

        if self._should_auto_commit():
            self._conn.commit()
        return cursor.rowcount > 0

    def delete_entry(self, entry_id: int) -> bool:
        """Delete an entry.

        Args:
            entry_id: The entry ID.

        Returns:
            True if the entry was deleted, False if not found.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        if self._should_auto_commit():
            self._conn.commit()
        return cursor.rowcount > 0

    def bulk_insert_entries(
        self,
        project_id: int,
        entries: list[dict[str, Any]],
    ) -> list[int]:
        """Bulk insert multiple entries efficiently.

        Args:
            project_id: Foreign key to the project.
            entries: List of dictionaries with entry data. Each dict should
                contain at least 'original' and may contain: file, map, event,
                page, command, speaker, context, status, notes.

        Returns:
            List of IDs for the inserted entries.

        Raises:
            DatabaseError: If a database error occurs.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        now = datetime.now(timezone.utc).isoformat()
        ids: list[int] = []

        cursor = self._conn.cursor()

        for entry_data in entries:
            cursor.execute("""
                INSERT INTO entries
                (project_id, file, map, event, page, command, speaker, context,
                 original, translated, status, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                entry_data.get("file"),
                entry_data.get("map"),
                entry_data.get("event"),
                entry_data.get("page"),
                entry_data.get("command"),
                entry_data.get("speaker"),
                entry_data.get("context"),
                entry_data["original"],
                None,
                entry_data.get("status", TranslationStatus.PENDING.value),
                entry_data.get("notes"),
                now,
                now,
            ))
            ids.append(cursor.lastrowid)  # type: ignore[arg-type]

        if self._should_auto_commit():
            self._conn.commit()
        return ids

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_entry_count(self, project_id: int) -> int:
        """Get the total number of entries for a project.

        Args:
            project_id: The project ID.

        Returns:
            The number of entries.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM entries WHERE project_id = ?",
            (project_id,)
        )
        return cursor.fetchone()[0]  # type: ignore[return-value]

    def get_status_counts(self, project_id: int) -> dict[str, int]:
        """Get counts of entries by status for a project.

        Args:
            project_id: The project ID.

        Returns:
            Dictionary mapping status to count.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM entries
            WHERE project_id = ?
            GROUP BY status
        """, (project_id,))

        return {row["status"]: row["count"] for row in cursor.fetchall()}

    def execute_query(
        self,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        """Execute a custom SELECT query.

        WARNING: Use with caution. This method bypasses the abstraction layer.

        Args:
            query: SQL SELECT query.
            params: Query parameters.

        Returns:
            List of result rows as dictionaries.

        Raises:
            DatabaseError: If a database error occurs.
        """
        if self._conn is None:
            raise RuntimeError("Database connection is not established")

        cursor = self._conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
