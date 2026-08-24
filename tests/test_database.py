"""Tests for DatabaseManager implementation.

These tests verify SQLite database operations including:
- Database creation and schema
- CRUD operations for projects and entries
- Transaction handling (commit/rollback)
- Unicode data persistence
- Escape code preservation
"""

import tempfile
from pathlib import Path

import pytest

from app.core.database import DatabaseManager, TranslationEntryRecord
from app.core.translation import TranslationStatus


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def db(temp_db_path):
    """Create a DatabaseManager instance."""
    manager = DatabaseManager(temp_db_path)
    yield manager
    manager.close()


class TestDatabaseCreation:
    """Test database creation and initialization."""

    def test_create_database_file(self, temp_db_path):
        """Test that database file is created."""
        assert not temp_db_path.exists()
        db = DatabaseManager(temp_db_path)
        assert temp_db_path.exists()
        db.close()

    def test_create_parent_directories(self, temp_db_path):
        """Test that parent directories are created."""
        nested_path = temp_db_path / "subdir" / "nested" / "test.db"
        assert not nested_path.parent.exists()
        db = DatabaseManager(nested_path)
        assert nested_path.parent.exists()
        db.close()

    def test_empty_path_raises(self, temp_db_path):
        """Test that empty path raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            DatabaseManager("")

    def test_schema_tables_created(self, db):
        """Test that all required tables are created."""
        tables = db.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = [t["name"] for t in tables]
        assert "projects" in table_names
        assert "entries" in table_names
        assert "glossary" in table_names
        assert "translation_memory" in table_names
        assert "schema_version" in table_names

    def test_schema_indexes_created(self, db):
        """Test that indexes are created."""
        indexes = db.execute_query(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        )
        index_names = [i["name"] for i in indexes]
        assert "idx_entries_project_id" in index_names
        assert "idx_entries_original" in index_names
        assert "idx_entries_file" in index_names
        assert "idx_entries_status" in index_names

    def test_schema_version_set(self, db):
        """Test that schema version is set."""
        result = db.execute_query("SELECT version FROM schema_version")
        assert len(result) == 1
        assert result[0]["version"] == 1


class TestProjectCRUD:
    """Test project CRUD operations."""

    def test_create_project(self, db):
        """Test creating a project."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
            engine_version="1.6.1",
            language_source="en",
            language_target="pt",
        )
        assert project_id > 0

    def test_get_project_by_id(self, db):
        """Test getting a project by ID."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        project = db.get_project(project_id)
        assert project is not None
        assert project["name"] == "Test Project"
        assert project["engine"] == "rpgmaker_mv"
        assert project["path"] == "/path/to/project"

    def test_get_project_by_path(self, db):
        """Test getting a project by path."""
        db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        project = db.get_project_by_path("/path/to/project")
        assert project is not None
        assert project["name"] == "Test Project"

    def test_get_nonexistent_project(self, db):
        """Test getting a project that doesn't exist."""
        project = db.get_project(99999)
        assert project is None

    def test_update_project(self, db):
        """Test updating a project."""
        project_id = db.create_project(
            name="Original Name",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        result = db.update_project(project_id, name="Updated Name")
        assert result is True
        project = db.get_project(project_id)
        assert project["name"] == "Updated Name"

    def test_update_nonexistent_project(self, db):
        """Test updating a project that doesn't exist."""
        result = db.update_project(99999, name="New Name")
        assert result is False

    def test_delete_project(self, db):
        """Test deleting a project."""
        project_id = db.create_project(
            name="To Delete",
            engine="rpgmaker_mv",
            path="/path/to/delete",
        )
        result = db.delete_project(project_id)
        assert result is True
        project = db.get_project(project_id)
        assert project is None

    def test_delete_nonexistent_project(self, db):
        """Test deleting a project that doesn't exist."""
        result = db.delete_project(99999)
        assert result is False

    def test_duplicate_path_raises(self, db):
        """Test that duplicate paths raise integrity error."""
        db.create_project(
            name="Project 1",
            engine="rpgmaker_mv",
            path="/unique/path",
        )
        # SQLite will raise IntegrityError on duplicate UNIQUE constraint
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            db.create_project(
                name="Project 2",
                engine="rpgmaker_mv",
                path="/unique/path",
            )


class TestEntryCRUD:
    """Test entry CRUD operations."""

    def test_insert_entry(self, db):
        """Test inserting an entry."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        entry_id = db.insert_entry(
            project_id=project_id,
            original="Hello, world!",
            file="www/data/System.json",
            context="game_title",
        )
        assert entry_id > 0

    def test_get_entry_by_id(self, db):
        """Test getting an entry by ID."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        entry_id = db.insert_entry(
            project_id=project_id,
            original="Test text",
            file="test.json",
            context="test_context",
        )
        entry = db.get_entry(entry_id)
        assert entry is not None
        assert entry.original == "Test text"
        assert entry.file == "test.json"
        assert entry.context == "test_context"
        assert entry.status == TranslationStatus.PENDING.value

    def test_get_nonexistent_entry(self, db):
        """Test getting an entry that doesn't exist."""
        entry = db.get_entry(99999)
        assert entry is None

    def test_get_entries_by_project(self, db):
        """Test getting all entries for a project."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        db.insert_entry(project_id=project_id, original="Entry 1")
        db.insert_entry(project_id=project_id, original="Entry 2")
        db.insert_entry(project_id=project_id, original="Entry 3")

        entries = db.get_entries_by_project(project_id)
        assert len(entries) == 3

    def test_get_entries_by_original(self, db):
        """Test getting entries by exact original text."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        db.insert_entry(project_id=project_id, original="Duplicate text")
        db.insert_entry(project_id=project_id, original="Unique text")
        db.insert_entry(project_id=project_id, original="Duplicate text")

        entries = db.get_entries_by_original("Duplicate text")
        assert len(entries) == 2

    def test_get_entries_containing_text(self, db):
        """Test getting entries containing text (partial match)."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        db.insert_entry(project_id=project_id, original="Hello world")
        db.insert_entry(project_id=project_id, original="Goodbye world")
        db.insert_entry(project_id=project_id, original="Hello there")

        entries = db.get_entries_containing_text("Hello", in_original=True)
        assert len(entries) == 2

    def test_update_entry_translation(self, db):
        """Test updating an entry's translation."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        entry_id = db.insert_entry(
            project_id=project_id,
            original="Hello",
        )
        result = db.update_entry_translation(
            entry_id=entry_id,
            translated="Olá",
            status=TranslationStatus.TRANSLATED.value,
        )
        assert result is True
        entry = db.get_entry(entry_id)
        assert entry.translated == "Olá"
        assert entry.status == TranslationStatus.TRANSLATED.value

    def test_update_entry_status(self, db):
        """Test updating an entry's status."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        entry_id = db.insert_entry(project_id=project_id, original="Test")
        result = db.update_entry_status(
            entry_id=entry_id,
            status=TranslationStatus.FAILED.value,
        )
        assert result is True
        entry = db.get_entry(entry_id)
        assert entry.status == TranslationStatus.FAILED.value

    def test_delete_entry(self, db):
        """Test deleting an entry."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        entry_id = db.insert_entry(project_id=project_id, original="To delete")
        result = db.delete_entry(entry_id)
        assert result is True
        entry = db.get_entry(entry_id)
        assert entry is None

    def test_bulk_insert_entries(self, db):
        """Test bulk inserting multiple entries."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )
        entries = [
            {"original": "Entry 1", "file": "file1.json"},
            {"original": "Entry 2", "file": "file2.json"},
            {"original": "Entry 3", "file": "file3.json"},
        ]
        ids = db.bulk_insert_entries(project_id, entries)
        assert len(ids) == 3
        assert all(id_ > 0 for id_ in ids)


class TestTransactionHandling:
    """Test transaction management."""

    def test_transaction_commit(self, db):
        """Test that transactions commit successfully."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )

        with db.transaction():
            db.insert_entry(project_id=project_id, original="Entry 1")
            db.insert_entry(project_id=project_id, original="Entry 2")

        # Verify entries were committed
        entries = db.get_entries_by_project(project_id)
        assert len(entries) == 2

    def test_transaction_rollback_on_exception(self, db):
        """Test that transactions rollback on exception."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )

        initial_count = db.get_entry_count(project_id)

        try:
            with db.transaction():
                db.insert_entry(project_id=project_id, original="Entry 1")
                db.insert_entry(project_id=project_id, original="Entry 2")
                raise ValueError("Simulated error")
        except ValueError:
            pass  # Expected

        # Verify entries were rolled back
        final_count = db.get_entry_count(project_id)
        assert final_count == initial_count

    def test_nested_operations_in_transaction(self, db):
        """Test multiple operations within a single transaction."""
        project_id = db.create_project(
            name="Test Project",
            engine="rpgmaker_mv",
            path="/path/to/project",
        )

        with db.transaction():
            entry_id = db.insert_entry(
                project_id=project_id,
                original="Original",
            )
            db.update_entry_translation(
                entry_id=entry_id,
                translated="Translated",
            )

        entry = db.get_entry(entry_id)
        assert entry.translated == "Translated"


class TestUnicodePersistence:
    """Test Unicode character persistence."""

    def test_unicode_characters(self, db):
        """Test that Unicode characters are stored correctly."""
        project_id = db.create_project(
            name="Unicode Test",
            engine="rpgmaker_mv",
            path="/path/to/unicode",
        )

        unicode_texts = [
            "日本語テスト",
            "한국어 테스트",
            "Ελληνικά",
            "עברית",
            "العربية",
            "Привет мир",
            "Ñoño español",
        ]

        for text in unicode_texts:
            db.insert_entry(project_id=project_id, original=text)

        entries = db.get_entries_by_project(project_id)
        originals = [e.original for e in entries]

        for text in unicode_texts:
            assert text in originals

    def test_unicode_translation(self, db):
        """Test that Unicode translations are stored correctly."""
        project_id = db.create_project(
            name="Unicode Test",
            engine="rpgmaker_mv",
            path="/path/to/unicode",
        )

        entry_id = db.insert_entry(
            project_id=project_id,
            original="Hello",
        )

        db.update_entry_translation(
            entry_id=entry_id,
            translated="こんにちは世界",
        )

        entry = db.get_entry(entry_id)
        assert entry.translated == "こんにちは世界"


class TestEscapeCodePreservation:
    """Test escape code and special character preservation."""

    def test_rpg_maker_escape_codes(self, db):
        """Test RPG Maker escape codes are preserved."""
        project_id = db.create_project(
            name="Escape Test",
            engine="rpgmaker_mv",
            path="/path/to/escape",
        )

        escape_codes = [
            r"\N[1]",
            r"\P[2]",
            r"\V[3]",
            r"\C[4]",
            r"\I[5]",
            r"\FS[16]",
            r".",
            r"!",
            r"\>",
            r"\<",
        ]

        for code in escape_codes:
            db.insert_entry(project_id=project_id, original=code)

        entries = db.get_entries_by_project(project_id)
        originals = [e.original for e in entries]

        for code in escape_codes:
            assert code in originals

    def test_mixed_text_with_escape_codes(self, db):
        """Test text mixed with escape codes."""
        project_id = db.create_project(
            name="Mixed Test",
            engine="rpgmaker_mv",
            path="/path/to/mixed",
        )

        mixed_texts = [
            r"Hello \N[1], how are you?",
            r"Item costs \V[10] gold.",
            r"\C[2]Red Text\C[0]",
            r"You received \I[5]!",
        ]

        for text in mixed_texts:
            entry_id = db.insert_entry(
                project_id=project_id,
                original=text,
            )
            db.update_entry_translation(
                entry_id=entry_id,
                translated=f"Translated: {text}",
            )

        entries = db.get_entries_by_project(project_id)
        for entry in entries:
            assert entry.original in mixed_texts
            assert entry.translated.startswith("Translated:")

    def test_newline_and_tab_characters(self, db):
        """Test newline and tab characters."""
        project_id = db.create_project(
            name="Whitespace Test",
            engine="rpgmaker_mv",
            path="/path/to/whitespace",
        )

        texts_with_whitespace = [
            "Line1\nLine2",
            "Column1\tColumn2",
            "Line1\nLine2\nLine3",
            "\tIndented",
        ]

        for text in texts_with_whitespace:
            db.insert_entry(project_id=project_id, original=text)

        entries = db.get_entries_by_project(project_id)
        originals = [e.original for e in entries]

        for text in texts_with_whitespace:
            assert text in originals


class TestPersistenceAcrossConnections:
    """Test data persistence across database connections."""

    def test_data_persists_after_close(self, temp_db_path):
        """Test that data persists after closing and reopening."""
        # First connection - insert data
        db1 = DatabaseManager(temp_db_path)
        project_id = db1.create_project(
            name="Persist Test",
            engine="rpgmaker_mv",
            path="/persist/test",
        )
        entry_id = db1.insert_entry(
            project_id=project_id,
            original="Persistent data",
        )
        db1.update_entry_translation(
            entry_id=entry_id,
            translated="Dados persistentes",
        )
        db1.close()

        # Second connection - read data
        db2 = DatabaseManager(temp_db_path)
        project = db2.get_project(project_id)
        assert project is not None
        assert project["name"] == "Persist Test"

        entries = db2.get_entries_by_project(project_id)
        assert len(entries) == 1
        assert entries[0].original == "Persistent data"
        assert entries[0].translated == "Dados persistentes"
        db2.close()

    def test_multiple_connections_isolation(self, temp_db_path):
        """Test that separate connections can operate independently."""
        db1 = DatabaseManager(temp_db_path)
        db2 = DatabaseManager(temp_db_path)

        project_id1 = db1.create_project(
            name="Project 1",
            engine="rpgmaker_mv",
            path="/project/1",
        )
        project_id2 = db2.create_project(
            name="Project 2",
            engine="rpgmaker_mv",
            path="/project/2",
        )

        # Both should see both projects (SQLite allows this)
        entries1 = db1.get_entries_by_project(project_id1)
        entries2 = db2.get_entries_by_project(project_id2)

        assert len(entries1) == 0
        assert len(entries2) == 0

        db1.close()
        db2.close()


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_entry_count(self, db):
        """Test counting entries."""
        project_id = db.create_project(
            name="Count Test",
            engine="rpgmaker_mv",
            path="/count/test",
        )

        assert db.get_entry_count(project_id) == 0

        db.insert_entry(project_id=project_id, original="Entry 1")
        db.insert_entry(project_id=project_id, original="Entry 2")
        db.insert_entry(project_id=project_id, original="Entry 3")

        assert db.get_entry_count(project_id) == 3

    def test_get_status_counts(self, db):
        """Test counting entries by status."""
        project_id = db.create_project(
            name="Status Count Test",
            engine="rpgmaker_mv",
            path="/status/test",
        )

        entry1 = db.insert_entry(project_id=project_id, original="Entry 1")
        entry2 = db.insert_entry(project_id=project_id, original="Entry 2")
        entry3 = db.insert_entry(project_id=project_id, original="Entry 3")

        db.update_entry_translation(entry1, "Tradução 1")
        db.update_entry_status(entry2, TranslationStatus.FAILED.value)

        counts = db.get_status_counts(project_id)
        assert counts.get(TranslationStatus.TRANSLATED.value, 0) == 1
        assert counts.get(TranslationStatus.FAILED.value, 0) == 1
        assert counts.get(TranslationStatus.PENDING.value, 0) == 1


class TestContextManager:
    """Test context manager usage."""

    def test_context_manager_closes_connection(self, temp_db_path):
        """Test that context manager properly closes connection."""
        with DatabaseManager(temp_db_path) as db:
            project_id = db.create_project(
                name="Context Test",
                engine="rpgmaker_mv",
                path="/context/test",
            )
            assert project_id > 0

        # After exiting context, connection should be closed
        # but we can still create a new one
        db2 = DatabaseManager(temp_db_path)
        project = db2.get_project(project_id)
        assert project is not None
        db2.close()
