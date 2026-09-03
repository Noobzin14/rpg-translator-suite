"""Basic Validator for RPG Maker MV translated projects.

This module provides validation capabilities for RPG Maker MV projects
before and after text reinsertion, ensuring JSON validity, structural
integrity, and escape code preservation.

The validator does NOT modify files - it only analyzes and returns
structured results.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from app.utils.token_protector import TokenProtector, SIMPLE_ESCAPE_PATTERN


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationIssueType(Enum):
    """Types of validation issues."""
    JSON_INVALID = "json_invalid"
    FILE_TRUNCATED = "file_truncated"
    ENCODING_INCOMPATIBLE = "encoding_incompatible"
    STRUCTURE_UNEXPECTED = "structure_unexpected"
    ARRAY_MISSING = "array_missing"
    OBJECT_MISSING = "object_missing"
    FIELD_MISSING = "field_missing"
    ESCAPE_CODE_REMOVED = "escape_code_removed"
    ESCAPE_CODE_DUPLICATED = "escape_code_duplicated"
    ESCAPE_CODE_ALTERED = "escape_code_altered"
    ENTRY_MISSING = "entry_missing"
    ENTRY_UNEXPECTED = "entry_unexpected"
    PLACEHOLDER_MISMATCH = "placeholder_mismatch"
    FILE_NOT_FOUND = "file_not_found"


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation issue.
    
    Attributes:
        issue_type: The type of issue detected.
        severity: The severity level of the issue.
        message: Human-readable description of the issue.
        file_path: Path to the file where the issue was found (if applicable).
        details: Additional context about the issue.
    """
    issue_type: ValidationIssueType
    severity: ValidationSeverity
    message: str
    file_path: Path | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of validating a project or file.
    
    Attributes:
        is_valid: Whether the validation passed (no errors/critical issues).
        issues: List of all validation issues found.
        file_path: Path to the validated file (if applicable).
        metadata: Additional metadata about the validation.
    """
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    file_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue to the result."""
        self.issues.append(issue)
        # Update validity based on severity
        if issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL):
            self.is_valid = False
    
    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
    
    @property
    def critical_count(self) -> int:
        """Count of critical-level issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.CRITICAL)


# Database arrays that must exist in valid MV projects
REQUIRED_DATABASE_ARRAYS = {
    "Actors.json": ["actors"],
    "Classes.json": ["classes"],
    "Skills.json": ["skills"],
    "Items.json": ["items"],
    "Weapons.json": ["weapons"],
    "Armors.json": ["armors"],
    "Enemies.json": ["enemies"],
    "States.json": ["states"],
    "Animations.json": ["animations"],
    "Tilesets.json": ["tilesets"],
    "CommonEvents.json": ["commonEvents"],
    "System.json": [],  # System.json has different structure
}

# Map file required structure
MAP_REQUIRED_FIELDS = ["events", "pages"]
MAP_EVENT_REQUIRED_FIELDS = ["pages", "list"]


class ProjectValidator:
    """Validates RPG Maker MV projects.
    
    This validator can check:
    - JSON validity
    - Structural integrity of database and map files
    - Escape code preservation
    - Entry count comparison between original and translated projects
    
    Usage:
        validator = ProjectValidator()
        
        # Validate a single JSON file
        result = validator.validate_json_file(path_to_json)
        
        # Validate entire project
        result = validator.validate_project(project_path)
        
        # Compare original vs translated
        result = validator.compare_projects(original_path, translated_path)
    """
    
    def __init__(self) -> None:
        """Initialize the ProjectValidator."""
        self._token_protector = TokenProtector()
    
    def validate_json_content(self, content: str, file_path: Path | None = None) -> ValidationResult:
        """Validate JSON content string.
        
        Args:
            content: The JSON content to validate.
            file_path: Optional path for error reporting.
            
        Returns:
            ValidationResult with any issues found.
        """
        result = ValidationResult(is_valid=True, file_path=file_path)
        
        # Check for empty/truncated content
        if not content or not content.strip():
            result.add_issue(ValidationIssue(
                issue_type=ValidationIssueType.FILE_TRUNCATED,
                severity=ValidationSeverity.CRITICAL,
                message="File is empty or contains only whitespace",
                file_path=file_path,
            ))
            return result
        
        # Try to parse JSON
        try:
            data = json.loads(content)
            result.metadata["parsed"] = True
            result.metadata["type"] = type(data).__name__
        except json.JSONDecodeError as e:
            result.add_issue(ValidationIssue(
                issue_type=ValidationIssueType.JSON_INVALID,
                severity=ValidationSeverity.CRITICAL,
                message=f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}",
                file_path=file_path,
                details={"line": e.lineno, "column": e.colno, "error": e.msg},
            ))
            return result
        
        return result
    
    def validate_json_file(self, file_path: Path, encoding: str = "utf-8") -> ValidationResult:
        """Validate a JSON file.
        
        Args:
            file_path: Path to the JSON file.
            encoding: Encoding to use when reading the file.
            
        Returns:
            ValidationResult with any issues found.
        """
        result = ValidationResult(is_valid=True, file_path=file_path)
        
        # Check file exists
        if not file_path.exists():
            result.add_issue(ValidationIssue(
                issue_type=ValidationIssueType.FILE_NOT_FOUND,
                severity=ValidationSeverity.CRITICAL,
                message=f"File not found: {file_path}",
                file_path=file_path,
            ))
            return result
        
        # Read and validate content
        try:
            content = file_path.read_text(encoding=encoding)
        except UnicodeDecodeError as e:
            result.add_issue(ValidationIssue(
                issue_type=ValidationIssueType.ENCODING_INCOMPATIBLE,
                severity=ValidationSeverity.CRITICAL,
                message=f"Encoding error: {e}",
                file_path=file_path,
                details={"encoding": encoding, "error": str(e)},
            ))
            return result
        except OSError as e:
            result.add_issue(ValidationIssue(
                issue_type=ValidationIssueType.FILE_TRUNCATED,
                severity=ValidationSeverity.CRITICAL,
                message=f"Cannot read file: {e}",
                file_path=file_path,
            ))
            return result
        
        # Validate JSON syntax
        json_result = self.validate_json_content(content, file_path)
        result.issues.extend(json_result.issues)
        result.is_valid = json_result.is_valid
        result.metadata.update(json_result.metadata)
        
        if not json_result.is_valid:
            return result
        
        # Parse for further validation
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return result  # Already reported
        
        # Validate structure based on file type
        self._validate_file_structure(data, file_path, result)
        
        return result
    
    def _validate_file_structure(
        self,
        data: Any,
        file_path: Path,
        result: ValidationResult,
    ) -> None:
        """Validate structure based on file type.
        
        Args:
            data: Parsed JSON data.
            file_path: Path to the file.
            result: ValidationResult to update.
        """
        if not isinstance(data, dict):
            result.add_issue(ValidationIssue(
                issue_type=ValidationIssueType.STRUCTURE_UNEXPECTED,
                severity=ValidationSeverity.ERROR,
                message="JSON root is not an object",
                file_path=file_path,
                details={"root_type": type(data).__name__},
            ))
            return
        
        filename = file_path.name
        
        # Check database files
        if filename in REQUIRED_DATABASE_ARRAYS:
            required_arrays = REQUIRED_DATABASE_ARRAYS[filename]
            for array_name in required_arrays:
                if array_name not in data:
                    result.add_issue(ValidationIssue(
                        issue_type=ValidationIssueType.ARRAY_MISSING,
                        severity=ValidationSeverity.ERROR,
                        message=f"Required array '{array_name}' is missing",
                        file_path=file_path,
                        details={"expected_array": array_name},
                    ))
                elif not isinstance(data[array_name], list):
                    result.add_issue(ValidationIssue(
                        issue_type=ValidationIssueType.STRUCTURE_UNEXPECTED,
                        severity=ValidationSeverity.ERROR,
                        message=f"Expected '{array_name}' to be an array",
                        file_path=file_path,
                        details={"field": array_name, "actual_type": type(data[array_name]).__name__},
                    ))
        
        # Check map files (MapXXX.json)
        if filename.startswith("Map") and filename.endswith(".json"):
            for field_name in MAP_REQUIRED_FIELDS:
                if field_name not in data:
                    result.add_issue(ValidationIssue(
                        issue_type=ValidationIssueType.FIELD_MISSING,
                        severity=ValidationSeverity.WARNING,
                        message=f"Expected field '{field_name}' not found in map file",
                        file_path=file_path,
                        details={"field": field_name},
                    ))
    
    def validate_escape_codes(
        self,
        original_text: str,
        translated_text: str,
        context: str | None = None,
    ) -> ValidationResult:
        """Validate that escape codes are preserved between original and translation.
        
        Args:
            original_text: Original text containing escape codes.
            translated_text: Translated text that should preserve escape codes.
            context: Optional context description for error messages.
            
        Returns:
            ValidationResult with any escape code issues.
        """
        result = ValidationResult(is_valid=True)
        result.metadata["original"] = original_text
        result.metadata["translated"] = translated_text
        if context:
            result.metadata["context"] = context
        
        # Extract escape codes from original
        original_tokens = SIMPLE_ESCAPE_PATTERN.findall(original_text)
        translated_tokens = SIMPLE_ESCAPE_PATTERN.findall(translated_text)
        
        result.metadata["original_token_count"] = len(original_tokens)
        result.metadata["translated_token_count"] = len(translated_tokens)
        
        # Check for removed tokens
        original_set = set(original_tokens)
        translated_set = set(translated_tokens)
        
        # Count occurrences
        from collections import Counter
        original_counts = Counter(original_tokens)
        translated_counts = Counter(translated_tokens)
        
        # Check for removed tokens
        for token in original_counts:
            if token not in translated_counts:
                result.add_issue(ValidationIssue(
                    issue_type=ValidationIssueType.ESCAPE_CODE_REMOVED,
                    severity=ValidationSeverity.ERROR,
                    message=f"Escape code removed: {token}",
                    details={
                        "token": token,
                        "original_count": original_counts[token],
                        "context": context,
                    },
                ))
            elif translated_counts[token] < original_counts[token]:
                result.add_issue(ValidationIssue(
                    issue_type=ValidationIssueType.ESCAPE_CODE_REMOVED,
                    severity=ValidationSeverity.ERROR,
                    message=f"Escape code count reduced: {token} ({original_counts[token]} -> {translated_counts[token]})",
                    details={
                        "token": token,
                        "original_count": original_counts[token],
                        "translated_count": translated_counts[token],
                        "context": context,
                    },
                ))
        
        # Check for duplicated/extra tokens
        for token in translated_counts:
            if token not in original_counts:
                result.add_issue(ValidationIssue(
                    issue_type=ValidationIssueType.ESCAPE_CODE_DUPLICATED,
                    severity=ValidationSeverity.ERROR,
                    message=f"Unexpected escape code added: {token}",
                    details={
                        "token": token,
                        "translated_count": translated_counts[token],
                        "context": context,
                    },
                ))
            elif translated_counts[token] > original_counts[token]:
                result.add_issue(ValidationIssue(
                    issue_type=ValidationIssueType.ESCAPE_CODE_DUPLICATED,
                    severity=ValidationSeverity.ERROR,
                    message=f"Escape code count increased: {token} ({original_counts[token]} -> {translated_counts[token]})",
                    details={
                        "token": token,
                        "original_count": original_counts[token],
                        "translated_count": translated_counts[token],
                        "context": context,
                    },
                ))
        
        # Check for altered tokens (different parameters)
        self._check_altered_tokens(original_tokens, translated_tokens, result, context)
        
        return result
    
    def _check_altered_tokens(
        self,
        original_tokens: list[str],
        translated_tokens: list[str],
        result: ValidationResult,
        context: str | None = None,
    ) -> None:
        """Check for altered token parameters.
        
        Args:
            original_tokens: List of tokens from original text.
            translated_tokens: List of tokens from translated text.
            result: ValidationResult to update.
            context: Optional context for error messages.
        """
        # Pattern to extract token type and parameter
        param_pattern = re.compile(r'\\([A-Za-z]+)\[(\d+)\]')
        
        original_params = {}
        translated_params = {}
        
        for i, token in enumerate(original_tokens):
            match = param_pattern.match(token)
            if match:
                token_type, param = match.groups()
                key = f"{token_type}_{i}"
                original_params[key] = (token_type, int(param), token)
        
        for i, token in enumerate(translated_tokens):
            match = param_pattern.match(token)
            if match:
                token_type, param = match.groups()
                key = f"{token_type}_{i}"
                translated_params[key] = (token_type, int(param), token)
        
        # Compare parameters for same-position tokens of same type
        for key, (orig_type, orig_param, orig_token) in original_params.items():
            if key in translated_params:
                trans_type, trans_param, trans_token = translated_params[key]
                if orig_type == trans_type and orig_param != trans_param:
                    result.add_issue(ValidationIssue(
                        issue_type=ValidationIssueType.ESCAPE_CODE_ALTERED,
                        severity=ValidationSeverity.ERROR,
                        message=f"Escape code parameter altered: {orig_token} -> {trans_token}",
                        details={
                            "original_token": orig_token,
                            "translated_token": trans_token,
                            "original_param": orig_param,
                            "translated_param": trans_param,
                            "context": context,
                        },
                    ))
    
    def compare_entries(
        self,
        original_data: dict[str, Any],
        translated_data: dict[str, Any],
        file_path: Path | None = None,
        array_field: str | None = None,
    ) -> ValidationResult:
        """Compare entry counts between original and translated data.
        
        Args:
            original_data: Original JSON data.
            translated_data: Translated JSON data.
            file_path: Optional path for error reporting.
            array_field: Specific array field to compare (optional).
            
        Returns:
            ValidationResult with any entry count issues.
        """
        result = ValidationResult(is_valid=True, file_path=file_path)
        result.metadata["comparison"] = True
        
        if array_field:
            fields_to_check = [array_field]
        else:
            # Determine fields based on common MV structure
            fields_to_check = []
            for filename, arrays in REQUIRED_DATABASE_ARRAYS.items():
                fields_to_check.extend(arrays)
            fields_to_check = list(set(fields_to_check))  # Remove duplicates
        
        for field_name in fields_to_check:
            orig_has = field_name in original_data
            trans_has = field_name in translated_data
            
            if orig_has and not trans_has:
                result.add_issue(ValidationIssue(
                    issue_type=ValidationIssueType.ENTRY_MISSING,
                    severity=ValidationSeverity.ERROR,
                    message=f"Array '{field_name}' missing in translation",
                    file_path=file_path,
                    details={"field": field_name},
                ))
                continue
            
            if not orig_has and trans_has:
                result.add_issue(ValidationIssue(
                    issue_type=ValidationIssueType.ENTRY_UNEXPECTED,
                    severity=ValidationSeverity.WARNING,
                    message=f"Array '{field_name}' unexpectedly present in translation",
                    file_path=file_path,
                    details={"field": field_name},
                ))
                continue
            
            if orig_has and trans_has:
                orig_array = original_data[field_name]
                trans_array = translated_data[field_name]
                
                if not isinstance(orig_array, list) or not isinstance(trans_array, list):
                    continue
                
                orig_count = len(orig_array)
                trans_count = len(trans_array)
                
                result.metadata[f"{field_name}_original_count"] = orig_count
                result.metadata[f"{field_name}_translated_count"] = trans_count
                
                if orig_count != trans_count:
                    result.add_issue(ValidationIssue(
                        issue_type=ValidationIssueType.ENTRY_MISSING if trans_count < orig_count else ValidationIssueType.ENTRY_UNEXPECTED,
                        severity=ValidationSeverity.ERROR if abs(orig_count - trans_count) > 0 else ValidationSeverity.WARNING,
                        message=f"Entry count mismatch for '{field_name}': {orig_count} -> {trans_count}",
                        file_path=file_path,
                        details={
                            "field": field_name,
                            "original_count": orig_count,
                            "translated_count": trans_count,
                        },
                    ))
        
        return result
    
    def validate_placeholders(
        self,
        original_text: str,
        translated_text: str,
        context: str | None = None,
    ) -> ValidationResult:
        """Validate placeholder consistency using TokenProtector.
        
        This method uses the existing TokenProtector to validate that
        placeholders are preserved correctly.
        
        Args:
            original_text: Original text.
            translated_text: Translated text.
            context: Optional context for error messages.
            
        Returns:
            ValidationResult with any placeholder issues.
        """
        result = ValidationResult(is_valid=True)
        result.metadata["context"] = context
        
        # Use TokenProtector's validation
        protect_result = self._token_protector.protect(original_text)
        is_valid, issues = self._token_protector.validate_translation(protect_result, translated_text)
        
        for issue_msg in issues:
            severity = ValidationSeverity.ERROR if "Missing" in issue_msg or "count" in issue_msg.lower() else ValidationSeverity.WARNING
            result.add_issue(ValidationIssue(
                issue_type=ValidationIssueType.PLACEHOLDER_MISMATCH,
                severity=severity,
                message=issue_msg,
                details={
                    "original": original_text,
                    "translated": translated_text,
                    "context": context,
                },
            ))
        
        result.is_valid = is_valid
        return result
    
    def validate_database_file(
        self,
        file_path: Path,
        encoding: str = "utf-8",
    ) -> ValidationResult:
        """Validate a database JSON file with MV-specific rules.
        
        Args:
            file_path: Path to the database file.
            encoding: Encoding to use when reading.
            
        Returns:
            ValidationResult with any issues found.
        """
        result = self.validate_json_file(file_path, encoding)
        
        if not result.is_valid:
            return result
        
        # Additional MV-specific validation
        try:
            content = file_path.read_text(encoding=encoding)
            data = json.loads(content)
        except (OSError, json.JSONDecodeError):
            return result  # Already reported
        
        filename = file_path.name
        
        # Validate specific database files
        if filename == "System.json":
            self._validate_system_json(data, file_path, result)
        elif filename == "Actors.json":
            self._validate_actors_json(data, file_path, result)
        
        return result
    
    def _validate_system_json(
        self,
        data: dict[str, Any],
        file_path: Path,
        result: ValidationResult,
    ) -> None:
        """Validate System.json structure.
        
        Args:
            data: Parsed System.json data.
            file_path: Path to the file.
            result: ValidationResult to update.
        """
        # gameTitle is typically present but not strictly required
        if "gameTitle" in data and not isinstance(data["gameTitle"], str):
            result.add_issue(ValidationIssue(
                issue_type=ValidationIssueType.STRUCTURE_UNEXPECTED,
                severity=ValidationSeverity.WARNING,
                message="gameTitle should be a string",
                file_path=file_path,
                details={"field": "gameTitle"},
            ))
    
    def _validate_actors_json(
        self,
        data: dict[str, Any],
        file_path: Path,
        result: ValidationResult,
    ) -> None:
        """Validate Actors.json structure.
        
        Args:
            data: Parsed Actors.json data.
            file_path: Path to the file.
            result: ValidationResult to update.
        """
        if "actors" not in data:
            return
        
        actors = data["actors"]
        if not isinstance(actors, list):
            return
        
        for i, actor in enumerate(actors):
            if not isinstance(actor, dict):
                result.add_issue(ValidationIssue(
                    issue_type=ValidationIssueType.STRUCTURE_UNEXPECTED,
                    severity=ValidationSeverity.WARNING,
                    message=f"Actor at index {i} is not an object",
                    file_path=file_path,
                    details={"index": i},
                ))
    
    def validate_map_file(
        self,
        file_path: Path,
        encoding: str = "utf-8",
    ) -> ValidationResult:
        """Validate a map JSON file.
        
        Args:
            file_path: Path to the map file.
            encoding: Encoding to use when reading.
            
        Returns:
            ValidationResult with any issues found.
        """
        result = self.validate_json_file(file_path, encoding)
        
        if not result.is_valid:
            return result
        
        # Additional map-specific validation would go here
        # For now, basic JSON validation is sufficient
        
        return result
    
    def validate_project(
        self,
        project_path: Path,
        encoding: str = "utf-8",
    ) -> ValidationResult:
        """Validate an entire RPG Maker MV project.
        
        Args:
            project_path: Path to the project directory.
            encoding: Encoding to use when reading files.
            
        Returns:
            ValidationResult with any issues found.
        """
        result = ValidationResult(is_valid=True, file_path=project_path)
        result.metadata["project_validation"] = True
        
        data_dir = project_path / "www" / "data"
        
        if not data_dir.exists():
            result.add_issue(ValidationIssue(
                issue_type=ValidationIssueType.FILE_NOT_FOUND,
                severity=ValidationSeverity.CRITICAL,
                message=f"Data directory not found: {data_dir}",
                file_path=data_dir,
            ))
            return result
        
        # Validate all database files
        db_files = [
            "Actors.json", "Classes.json", "Skills.json", "Items.json",
            "Weapons.json", "Armors.json", "Enemies.json", "States.json",
            "Animations.json", "Tilesets.json", "CommonEvents.json", "System.json",
        ]
        
        for db_file in db_files:
            file_path = data_dir / db_file
            if file_path.exists():
                file_result = self.validate_database_file(file_path, encoding)
                result.issues.extend(file_result.issues)
                if not file_result.is_valid:
                    result.is_valid = False
        
        # Validate map files
        map_files = sorted(data_dir.glob("Map*.json"))
        for map_file in map_files:
            file_result = self.validate_map_file(map_file, encoding)
            result.issues.extend(file_result.issues)
            if not file_result.is_valid:
                result.is_valid = False
        
        result.metadata["files_checked"] = len(db_files) + len(map_files)
        
        return result
    
    def compare_projects(
        self,
        original_path: Path,
        translated_path: Path,
        encoding: str = "utf-8",
    ) -> ValidationResult:
        """Compare original and translated projects.
        
        Args:
            original_path: Path to the original project.
            translated_path: Path to the translated project.
            encoding: Encoding to use when reading files.
            
        Returns:
            ValidationResult with any comparison issues.
        """
        result = ValidationResult(is_valid=True)
        result.metadata["comparison"] = True
        result.metadata["original_path"] = str(original_path)
        result.metadata["translated_path"] = str(translated_path)
        
        data_dir_orig = original_path / "www" / "data"
        data_dir_trans = translated_path / "www" / "data"
        
        # Compare database files
        db_files = list(REQUIRED_DATABASE_ARRAYS.keys())
        
        for db_file in db_files:
            orig_path = data_dir_orig / db_file
            trans_path = data_dir_trans / db_file
            
            if not orig_path.exists():
                continue
            if not trans_path.exists():
                result.add_issue(ValidationIssue(
                    issue_type=ValidationIssueType.FILE_NOT_FOUND,
                    severity=ValidationSeverity.ERROR,
                    message=f"Translated file missing: {db_file}",
                    file_path=trans_path,
                ))
                continue
            
            try:
                orig_content = orig_path.read_text(encoding=encoding)
                trans_content = trans_path.read_text(encoding=encoding)
                
                orig_data = json.loads(orig_content)
                trans_data = json.loads(trans_content)
                
                # Compare entry counts
                comparison_result = self.compare_entries(orig_data, trans_data, trans_path)
                result.issues.extend(comparison_result.issues)
                if not comparison_result.is_valid:
                    result.is_valid = False
                    
            except (OSError, json.JSONDecodeError) as e:
                result.add_issue(ValidationIssue(
                    issue_type=ValidationIssueType.JSON_INVALID,
                    severity=ValidationSeverity.ERROR,
                    message=f"Error comparing {db_file}: {e}",
                    file_path=trans_path,
                ))
        
        return result
