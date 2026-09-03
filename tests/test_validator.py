"""Tests for ProjectValidator implementation.

These tests verify that the ProjectValidator correctly:
1. Validates JSON syntax
2. Validates MV project structure
3. Detects escape code issues
4. Compares original vs translated projects
5. Returns structured results
"""

import json
import tempfile
from pathlib import Path

import pytest

from app.services.validator import (
    ProjectValidator,
    ValidationIssue,
    ValidationIssueType,
    ValidationResult,
    ValidationSeverity,
)


@pytest.fixture
def validator():
    """Create a ProjectValidator instance."""
    return ProjectValidator()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestValidationResult:
    """Test ValidationResult data class."""

    def test_create_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid
        assert len(result.issues) == 0
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.critical_count == 0

    def test_add_issue_updates_validity(self):
        """Test that adding error issue updates validity."""
        result = ValidationResult(is_valid=True)
        result.add_issue(ValidationIssue(
            issue_type=ValidationIssueType.JSON_INVALID,
            severity=ValidationSeverity.ERROR,
            message="Invalid JSON",
        ))
        assert not result.is_valid
        assert result.error_count == 1

    def test_add_warning_keeps_valid(self):
        """Test that adding warning keeps validity."""
        result = ValidationResult(is_valid=True)
        result.add_issue(ValidationIssue(
            issue_type=ValidationIssueType.FIELD_MISSING,
            severity=ValidationSeverity.WARNING,
            message="Field missing",
        ))
        assert result.is_valid
        assert result.warning_count == 1

    def test_add_critical_invalidates(self):
        """Test that adding critical issue invalidates result."""
        result = ValidationResult(is_valid=True)
        result.add_issue(ValidationIssue(
            issue_type=ValidationIssueType.FILE_NOT_FOUND,
            severity=ValidationSeverity.CRITICAL,
            message="File not found",
        ))
        assert not result.is_valid
        assert result.critical_count == 1


class TestJSONValidation:
    """Test JSON validation functionality."""

    def test_valid_json(self, validator, temp_dir):
        """Test validation of valid JSON."""
        json_file = temp_dir / "valid.json"
        json_file.write_text('{"name": "test", "value": 123}', encoding="utf-8")
        
        result = validator.validate_json_file(json_file)
        
        assert result.is_valid
        assert result.metadata.get("parsed") is True
        assert len(result.issues) == 0

    def test_invalid_json_syntax(self, validator, temp_dir):
        """Test validation of invalid JSON syntax."""
        json_file = temp_dir / "invalid.json"
        json_file.write_text('{"name": "test", value: 123}', encoding="utf-8")  # Missing quotes
        
        result = validator.validate_json_file(json_file)
        
        assert not result.is_valid
        assert result.critical_count > 0
        assert any(i.issue_type == ValidationIssueType.JSON_INVALID for i in result.issues)

    def test_empty_file(self, validator, temp_dir):
        """Test validation of empty file."""
        json_file = temp_dir / "empty.json"
        json_file.write_text("", encoding="utf-8")
        
        result = validator.validate_json_file(json_file)
        
        assert not result.is_valid
        assert result.critical_count > 0
        assert any(i.issue_type == ValidationIssueType.FILE_TRUNCATED for i in result.issues)

    def test_whitespace_only_file(self, validator, temp_dir):
        """Test validation of whitespace-only file."""
        json_file = temp_dir / "whitespace.json"
        json_file.write_text("   \n\t  ", encoding="utf-8")
        
        result = validator.validate_json_file(json_file)
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.FILE_TRUNCATED for i in result.issues)

    def test_file_not_found(self, validator, temp_dir):
        """Test validation of non-existent file."""
        json_file = temp_dir / "nonexistent.json"
        
        result = validator.validate_json_file(json_file)
        
        assert not result.is_valid
        assert result.critical_count > 0
        assert any(i.issue_type == ValidationIssueType.FILE_NOT_FOUND for i in result.issues)

    def test_json_array_root(self, validator, temp_dir):
        """Test validation of JSON with array root."""
        json_file = temp_dir / "array.json"
        json_file.write_text('[1, 2, 3]', encoding="utf-8")
        
        result = validator.validate_json_content(json_file.read_text(encoding="utf-8"), json_file)
        
        assert result.is_valid
        assert result.metadata.get("type") == "list"


class TestMVStructureValidation:
    """Test RPG Maker MV structure validation."""

    def test_valid_actors_json(self, validator, temp_dir):
        """Test validation of valid Actors.json."""
        actors_file = temp_dir / "Actors.json"
        data = {"actors": [{"id": 1, "name": "Hero"}]}
        actors_file.write_text(json.dumps(data), encoding="utf-8")
        
        result = validator.validate_database_file(actors_file)
        
        assert result.is_valid

    def test_missing_actors_array(self, validator, temp_dir):
        """Test validation when actors array is missing."""
        actors_file = temp_dir / "Actors.json"
        data = {"otherField": "value"}  # Missing 'actors' array
        actors_file.write_text(json.dumps(data), encoding="utf-8")
        
        result = validator.validate_database_file(actors_file)
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.ARRAY_MISSING for i in result.issues)

    def test_valid_system_json(self, validator, temp_dir):
        """Test validation of valid System.json."""
        system_file = temp_dir / "System.json"
        data = {"gameTitle": "Test Game", "version": 1}
        system_file.write_text(json.dumps(data), encoding="utf-8")
        
        result = validator.validate_database_file(system_file)
        
        assert result.is_valid

    def test_valid_map_file(self, validator, temp_dir):
        """Test validation of valid map file."""
        map_file = temp_dir / "Map001.json"
        data = {"events": [], "pages": []}
        map_file.write_text(json.dumps(data), encoding="utf-8")
        
        result = validator.validate_map_file(map_file)
        
        assert result.is_valid


class TestEscapeCodeValidation:
    """Test escape code validation functionality."""

    def test_escape_codes_preserved(self, validator):
        """Test validation when escape codes are preserved."""
        original = "Hello \\N[1], you have \\V[5] gold."
        translated = "Olá \\N[1], você tem \\V[5] de ouro."
        
        result = validator.validate_escape_codes(original, translated)
        
        assert result.is_valid
        assert len(result.issues) == 0

    def test_escape_code_removed(self, validator):
        """Test detection of removed escape code."""
        original = "Hello \\N[1]!"
        translated = "Hello world!"  # Token removed
        
        result = validator.validate_escape_codes(original, translated)
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.ESCAPE_CODE_REMOVED for i in result.issues)

    def test_escape_code_duplicated(self, validator):
        """Test detection of duplicated escape code."""
        original = "Hello \\N[1]!"
        translated = "Hello \\N[1] \\N[1]!"  # Token duplicated
        
        result = validator.validate_escape_codes(original, translated)
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.ESCAPE_CODE_DUPLICATED for i in result.issues)

    def test_escape_code_altered_parameter(self, validator):
        """Test detection of altered escape code parameter."""
        original = "\\N[1] has \\V[5] gold."
        translated = "\\N[2] has \\V[5] gold."  # Actor ID changed
        
        result = validator.validate_escape_codes(original, translated)
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.ESCAPE_CODE_ALTERED for i in result.issues)

    def test_multiple_tokens_same_type(self, validator):
        """Test validation with multiple tokens of same type."""
        original = "\\N[1] met \\N[2] and \\N[1] again."
        translated = "\\N[1] encontrou \\N[2] e \\N[1] novamente."
        
        result = validator.validate_escape_codes(original, translated)
        
        assert result.is_valid

    def test_mixed_token_types(self, validator):
        """Test validation with mixed token types."""
        original = "\\N[1]: Welcome to \\C[2]the castle\\C[0]! \\V[10] points."
        translated = "\\N[1]: Bem-vindo ao \\C[2]castelo\\C[0]! \\V[10] pontos."
        
        result = validator.validate_escape_codes(original, translated)
        
        assert result.is_valid

    def test_unicode_with_escape_codes(self, validator):
        """Test validation with Unicode text and escape codes."""
        original = "こんにちは \\N[1] さん！"
        translated = "Welcome \\N[1]-san!"
        
        result = validator.validate_escape_codes(original, translated)
        
        assert result.is_valid


class TestPlaceholderValidation:
    """Test placeholder validation using TokenProtector integration."""

    def test_placeholders_preserved(self, validator):
        """Test validation when placeholders are preserved."""
        original = "Hello \\N[1]!"
        translated = "Olá __TOKEN_0__!"
        
        result = validator.validate_placeholders(original, translated)
        
        assert result.is_valid

    def test_placeholder_removed(self, validator):
        """Test detection of removed placeholder."""
        original = "Hello \\N[1]!"
        translated = "Olá mundo!"  # Placeholder removed
        
        result = validator.validate_placeholders(original, translated)
        
        assert not result.is_valid
        assert any("Missing" in i.message for i in result.issues)

    def test_placeholder_count_mismatch(self, validator):
        """Test detection of placeholder count mismatch."""
        original = "\\N[1] and \\V[2]"
        translated = "__TOKEN_0__ only"  # One placeholder missing
        
        result = validator.validate_placeholders(original, translated)
        
        assert not result.is_valid
        assert any("count" in i.message.lower() or "Missing" in i.message for i in result.issues)


class TestEntryComparison:
    """Test entry count comparison between original and translated."""

    def test_equal_entry_counts(self, validator):
        """Test comparison with equal entry counts."""
        original = {"actors": [{"id": 1}, {"id": 2}]}
        translated = {"actors": [{"id": 1}, {"id": 2}]}
        
        result = validator.compare_entries(original, translated, array_field="actors")
        
        assert result.is_valid
        assert result.metadata.get("actors_original_count") == 2
        assert result.metadata.get("actors_translated_count") == 2

    def test_missing_entries(self, validator):
        """Test detection of missing entries."""
        original = {"actors": [{"id": 1}, {"id": 2}, {"id": 3}]}
        translated = {"actors": [{"id": 1}, {"id": 2}]}  # One entry missing
        
        result = validator.compare_entries(original, translated, array_field="actors")
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.ENTRY_MISSING for i in result.issues)

    def test_unexpected_entries(self, validator):
        """Test detection of unexpected entries."""
        original = {"actors": [{"id": 1}]}
        translated = {"actors": [{"id": 1}, {"id": 2}]}  # Extra entry
        
        result = validator.compare_entries(original, translated, array_field="actors")
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.ENTRY_UNEXPECTED for i in result.issues)

    def test_missing_array_in_translation(self, validator):
        """Test detection of missing array in translation."""
        original = {"actors": [{"id": 1}]}
        translated = {}  # actors array missing
        
        result = validator.compare_entries(original, translated, array_field="actors")
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.ENTRY_MISSING for i in result.issues)


class TestProjectValidation:
    """Test full project validation."""

    def test_valid_project_structure(self, validator, temp_dir):
        """Test validation of valid project structure."""
        # Create minimal valid project
        data_dir = temp_dir / "www" / "data"
        data_dir.mkdir(parents=True)
        
        # Create required database files
        for db_file, content in [
            ("Actors.json", '{"actors": []}'),
            ("Classes.json", '{"classes": []}'),
            ("Skills.json", '{"skills": []}'),
            ("Items.json", '{"items": []}'),
            ("Weapons.json", '{"weapons": []}'),
            ("Armors.json", '{"armors": []}'),
            ("Enemies.json", '{"enemies": []}'),
            ("States.json", '{"states": []}'),
            ("Animations.json", '{"animations": []}'),
            ("Tilesets.json", '{"tilesets": []}'),
            ("CommonEvents.json", '{"commonEvents": []}'),
            ("System.json", '{"gameTitle": "Test"}'),
        ]:
            (data_dir / db_file).write_text(content, encoding="utf-8")
        
        result = validator.validate_project(temp_dir)
        
        assert result.is_valid
        assert result.metadata.get("project_validation") is True
        assert result.metadata.get("files_checked", 0) > 0

    def test_missing_data_directory(self, validator, temp_dir):
        """Test validation when data directory is missing."""
        result = validator.validate_project(temp_dir)
        
        assert not result.is_valid
        assert result.critical_count > 0
        assert any(i.issue_type == ValidationIssueType.FILE_NOT_FOUND for i in result.issues)

    def test_project_with_map_files(self, validator, temp_dir):
        """Test validation of project with map files."""
        data_dir = temp_dir / "www" / "data"
        data_dir.mkdir(parents=True)
        
        # Create System.json
        (data_dir / "System.json").write_text('{"gameTitle": "Test"}', encoding="utf-8")
        
        # Create map files
        (data_dir / "Map001.json").write_text('{"events": [], "pages": []}', encoding="utf-8")
        (data_dir / "Map002.json").write_text('{"events": [], "pages": []}', encoding="utf-8")
        
        result = validator.validate_project(temp_dir)
        
        # Should be valid (missing optional files generate warnings, not errors)
        assert result.metadata.get("files_checked", 0) >= 3


class TestProjectComparison:
    """Test comparison between original and translated projects."""

    def test_identical_projects(self, validator, temp_dir):
        """Test comparison of identical projects."""
        # Create original project
        orig_data = temp_dir / "original" / "www" / "data"
        orig_data.mkdir(parents=True)
        (orig_data / "Actors.json").write_text('{"actors": [{"id": 1}]}', encoding="utf-8")
        
        # Create translated project (identical structure)
        trans_data = temp_dir / "translated" / "www" / "data"
        trans_data.mkdir(parents=True)
        (trans_data / "Actors.json").write_text('{"actors": [{"id": 1}]}', encoding="utf-8")
        
        result = validator.compare_projects(temp_dir / "original", temp_dir / "translated")
        
        assert result.is_valid
        assert result.metadata.get("comparison") is True

    def test_missing_translated_file(self, validator, temp_dir):
        """Test comparison when translated file is missing."""
        # Create original project
        orig_data = temp_dir / "original" / "www" / "data"
        orig_data.mkdir(parents=True)
        (orig_data / "Actors.json").write_text('{"actors": [{"id": 1}]}', encoding="utf-8")
        
        # Create translated project without Actors.json
        trans_data = temp_dir / "translated" / "www" / "data"
        trans_data.mkdir(parents=True)
        (trans_data / "System.json").write_text('{"gameTitle": "Test"}', encoding="utf-8")
        
        result = validator.compare_projects(temp_dir / "original", temp_dir / "translated")
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.FILE_NOT_FOUND for i in result.issues)

    def test_entry_count_mismatch(self, validator, temp_dir):
        """Test comparison with entry count mismatch."""
        # Create original project
        orig_data = temp_dir / "original" / "www" / "data"
        orig_data.mkdir(parents=True)
        (orig_data / "Actors.json").write_text('{"actors": [{"id": 1}, {"id": 2}]}', encoding="utf-8")
        
        # Create translated project with different count
        trans_data = temp_dir / "translated" / "www" / "data"
        trans_data.mkdir(parents=True)
        (trans_data / "Actors.json").write_text('{"actors": [{"id": 1}]}', encoding="utf-8")
        
        result = validator.compare_projects(temp_dir / "original", temp_dir / "translated")
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.ENTRY_MISSING for i in result.issues)


class TestCorruptionDetection:
    """Test detection of deliberate corruption scenarios."""

    def test_token_removed_from_translation(self, validator):
        """Test detection of token removal (corruption scenario 1)."""
        original = "Olá \\N[1]"
        translated = "Hello"  # Token completely removed
        
        result = validator.validate_escape_codes(original, translated)
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.ESCAPE_CODE_REMOVED for i in result.issues)

    def test_token_parameter_altered(self, validator):
        """Test detection of token parameter alteration (corruption scenario 2)."""
        original = "\\N[1] possui \\V[5]"
        translated = "\\N[2] has \\V[5]"  # Actor ID changed from 1 to 2
        
        result = validator.validate_escape_codes(original, translated)
        
        assert not result.is_valid
        assert any(i.issue_type == ValidationIssueType.ESCAPE_CODE_ALTERED for i in result.issues)

    def test_multiple_corruptions(self, validator):
        """Test detection of multiple corruption types."""
        original = "\\N[1] has \\V[5] gold and \\I[10] item."
        translated = "\\N[2] has gold."  # Multiple issues: altered N, removed V, removed I
        
        result = validator.validate_escape_codes(original, translated)
        
        assert not result.is_valid
        issue_types = {i.issue_type for i in result.issues}
        assert ValidationIssueType.ESCAPE_CODE_REMOVED in issue_types
        assert ValidationIssueType.ESCAPE_CODE_ALTERED in issue_types


class TestIntegrationScenarios:
    """Test integration scenarios simulating real usage."""

    def test_full_validation_workflow(self, validator, temp_dir):
        """Test complete validation workflow."""
        # Create test file
        json_file = temp_dir / "test.json"
        data = {
            "actors": [
                {"id": 1, "name": "\\N[1] the Hero"},
                {"id": 2, "name": "\\N[2] the Villain"},
            ]
        }
        json_file.write_text(json.dumps(data), encoding="utf-8")
        
        # Validate file
        file_result = validator.validate_json_file(json_file)
        assert file_result.is_valid
        
        # Validate escape codes in extracted text
        escape_result = validator.validate_escape_codes(
            "\\N[1] the Hero",
            "\\N[1] o Herói"
        )
        assert escape_result.is_valid

    def test_validator_with_token_protector_integration(self, validator):
        """Test validator integration with TokenProtector."""
        # This tests that the validator properly uses TokenProtector
        original = "Hello \\N[1] and \\V[2]!"
        translated = "Olá __TOKEN_0__ e __TOKEN_1__!"
        
        result = validator.validate_placeholders(original, translated)
        
        assert result.is_valid
        assert len(result.issues) == 0
