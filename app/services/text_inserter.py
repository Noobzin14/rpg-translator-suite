"""Text Inserter service for RPG Translator Suite.

This module provides the TextInserter class responsible for reinserting
translated text back into RPG Maker MV project files using metadata from
TranslationEntry objects.

The TextInserter:
1. Receives translated entries with location metadata
2. Locates the exact original text in source files
3. Substitutes with translated text
4. Preserves JSON structure and non-translated fields
5. Preserves escape codes
6. Validates before writing
7. Operates safely on copies/test projects
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from app.core.translation import TranslationEntry


class InsertStatus(str, Enum):
    """Possible statuses for a text insertion operation."""

    SUCCESS = "success"
    FAILED = "failed"
    MISMATCH = "mismatch"  # Original text doesn't match
    NOT_FOUND = "not_found"  # Location not found
    INVALID_LOCATION = "invalid_location"  # Metadata is invalid
    FILE_NOT_FOUND = "file_not_found"
    JSON_INVALID = "json_invalid"


@dataclass(frozen=True)
class InsertIssue:
    """Represents an issue found during text insertion.

    Attributes:
        severity: The severity level of this issue.
        code: A machine-readable code identifying the issue type.
        message: A human-readable description of the issue.
        entry_id: Optional ID of the related translation entry.
        source_file: Optional path to the source file.
    """

    severity: str  # "info", "warning", "error"
    code: str
    message: str
    entry_id: str | None = None
    source_file: Path | None = None


@dataclass(frozen=True)
class InsertResult:
    """Result of inserting a single translation entry.

    Attributes:
        entry_id: Identifier of the processed entry.
        status: The insertion status for this entry.
        original_text: The original text that was replaced.
        translated_text: The new text that was inserted.
        source_file: Path to the source file.
        issues: Tuple of issues encountered during insertion.
    """

    entry_id: str
    status: InsertStatus
    original_text: str
    translated_text: str | None = None
    source_file: Path | None = None
    issues: tuple[InsertIssue, ...] = ()


@dataclass
class InsertBatchResult:
    """Aggregated result of inserting multiple translations.

    Attributes:
        results: Tuple of individual insertion results.
        modified_files: Set of files that were modified.
        issues: Tuple of batch-level issues.
    """

    results: tuple[InsertResult, ...] = ()
    modified_files: set[Path] = field(default_factory=set)
    issues: tuple[InsertIssue, ...] = ()


class TextInserter:
    """Service for inserting translated text into RPG Maker MV files.

    The TextInserter uses metadata from TranslationEntry objects to locate
    the exact position of original text in source files and replaces it with
    translated text while preserving JSON structure and escape codes.

    Attributes:
        project_path: Path to the source RPG Maker MV project.
        output_path: Path where modified files will be written.
    """

    def __init__(self, project_path: Path, output_path: Path):
        """Initialize the TextInserter.

        Args:
            project_path: Path to the source RPG Maker MV project.
            output_path: Path where modified files will be written.
        """
        self.project_path = project_path.resolve()
        self.output_path = output_path.resolve()

    def insert(self, translations: list[TranslationEntry]) -> InsertBatchResult:
        """Insert translated text into source files.

        Args:
            translations: List of TranslationEntry objects with translated text.

        Returns:
            InsertBatchResult containing results for all entries.
        """
        results: list[InsertResult] = []
        modified_files: set[Path] = set()
        issues: list[InsertIssue] = []

        # Group translations by source file for efficient processing
        translations_by_file: dict[Path, list[TranslationEntry]] = {}
        for entry in translations:
            if entry.source_file:
                source_path = self.project_path / entry.source_file
                if source_path not in translations_by_file:
                    translations_by_file[source_path] = []
                translations_by_file[source_path].append(entry)

        # Process each file
        for source_path, entries in translations_by_file.items():
            file_results, file_modified, file_issues = self._process_file(
                source_path, entries
            )
            results.extend(file_results)
            if file_modified:
                modified_files.add(source_path)
            issues.extend(file_issues)

        return InsertBatchResult(
            results=tuple(results),
            modified_files=modified_files,
            issues=tuple(issues),
        )

    def _process_file(
        self, source_path: Path, entries: list[TranslationEntry]
    ) -> tuple[list[InsertResult], bool, list[InsertIssue]]:
        """Process all translations for a single file.

        Args:
            source_path: Path to the source file.
            entries: List of translation entries for this file.

        Returns:
            Tuple of (results, modified, issues).
        """
        results: list[InsertResult] = []
        issues: list[InsertIssue] = []

        # Check if file exists
        if not source_path.exists():
            issue = InsertIssue(
                severity="error",
                code="file_not_found",
                message=f"Source file not found: {source_path}",
            )
            issues.append(issue)
            for entry in entries:
                results.append(
                    InsertResult(
                        entry_id=entry.id,
                        status=InsertStatus.FILE_NOT_FOUND,
                        original_text=entry.original_text,
                        source_file=source_path,
                        issues=(issue,),
                    )
                )
            return results, False, issues

        # Load and parse JSON
        try:
            content = source_path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            issue = InsertIssue(
                severity="error",
                code="json_invalid",
                message=f"Invalid JSON in {source_path.name}: {exc}",
            )
            issues.append(issue)
            for entry in entries:
                results.append(
                    InsertResult(
                        entry_id=entry.id,
                        status=InsertStatus.JSON_INVALID,
                        original_text=entry.original_text,
                        source_file=source_path,
                        issues=(issue,),
                    )
                )
            return results, False, issues
        except OSError as exc:
            issue = InsertIssue(
                severity="error",
                code="read_error",
                message=f"Failed to read {source_path.name}: {exc}",
            )
            issues.append(issue)
            for entry in entries:
                results.append(
                    InsertResult(
                        entry_id=entry.id,
                        status=InsertStatus.FAILED,
                        original_text=entry.original_text,
                        source_file=source_path,
                        issues=(issue,),
                    )
                )
            return results, False, issues

        # Process each entry
        modified = False
        for entry in entries:
            result = self._insert_entry(data, entry, source_path)
            results.append(result)
            if result.status == InsertStatus.SUCCESS:
                modified = True

        # Write modified file if any changes were made
        if modified:
            self._write_file(source_path, data)

        return results, modified, issues

    def _insert_entry(
        self, data: Any, entry: TranslationEntry, source_path: Path
    ) -> InsertResult:
        """Insert a single translation entry into the data structure.

        Args:
            data: The JSON data structure (dict or list).
            entry: The translation entry to insert.
            source_path: Path to the source file (for error reporting).

        Returns:
            InsertResult indicating the outcome.
        """
        metadata = entry.metadata or {}

        # Determine the source kind and dispatch to appropriate handler
        source_kind = metadata.get("source_kind")

        if source_kind == "system":
            return self._insert_system(data, entry, source_path)
        elif source_kind == "config":
            return self._insert_config(data, entry, source_path)
        elif source_kind in [
            "actor",
            "class",
            "skill",
            "item",
            "weapon",
            "armor",
            "enemy",
            "state",
            "animation",
            "tileset",
        ]:
            return self._insert_database(data, entry, source_path)
        elif source_kind == "commonEvent":
            return self._insert_common_event(data, entry, source_path)
        elif source_kind == "map":
            return self._insert_map(data, entry, source_path)
        else:
            issue = InsertIssue(
                severity="error",
                code="invalid_location",
                message=f"Unknown source_kind: {source_kind}",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.INVALID_LOCATION,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

    def _insert_system(
        self, data: Any, entry: TranslationEntry, source_path: Path
    ) -> InsertResult:
        """Insert translation into System.json data.

        Args:
            data: The System.json data structure.
            entry: The translation entry.
            source_path: Path to the source file.

        Returns:
            InsertResult indicating the outcome.
        """
        if not isinstance(data, dict):
            issue = InsertIssue(
                severity="error",
                code="invalid_structure",
                message="System.json must be a dictionary",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        metadata = entry.metadata or {}
        field_path = metadata.get("field", "")

        # Handle gameTitle
        if field_path == "gameTitle":
            return self._validate_and_set(
                data, "gameTitle", entry, source_path
            )

        # Handle terms (e.g., terms.basic.party)
        if field_path.startswith("terms."):
            parts = field_path.split(".")
            if len(parts) >= 3:
                category = parts[1]
                term_field = parts[2]
                if category in data.get("terms", {}) and isinstance(
                    data["terms"], dict
                ):
                    return self._validate_and_set(
                        data["terms"], category, entry, source_path, nested_field=term_field
                    )

        # Handle vehicle names (e.g., vehicles[0].name)
        if field_path.startswith("vehicles[") and field_path.endswith("].name"):
            idx_str = field_path.split("[")[1].split("]")[0]
            try:
                idx = int(idx_str)
                vehicles = data.get("vehicles", [])
                if isinstance(vehicles, list) and idx < len(vehicles):
                    return self._validate_and_set(
                        vehicles[idx], "name", entry, source_path
                    )
            except (ValueError, IndexError):
                pass

        issue = InsertIssue(
            severity="error",
            code="field_not_found",
            message=f"Field not found in System.json: {field_path}",
            entry_id=entry.id,
            source_file=source_path,
        )
        return InsertResult(
            entry_id=entry.id,
            status=InsertStatus.NOT_FOUND,
            original_text=entry.original_text,
            source_file=source_path,
            issues=(issue,),
        )

    def _insert_config(
        self, data: Any, entry: TranslationEntry, source_path: Path
    ) -> InsertResult:
        """Insert translation into package.json config data.

        Args:
            data: The package.json data structure.
            entry: The translation entry.
            source_path: Path to the source file.

        Returns:
            InsertResult indicating the outcome.
        """
        if not isinstance(data, dict):
            issue = InsertIssue(
                severity="error",
                code="invalid_structure",
                message="package.json must be a dictionary",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        metadata = entry.metadata or {}
        field_name = metadata.get("field", "name")

        return self._validate_and_set(data, field_name, entry, source_path)

    def _insert_database(
        self, data: Any, entry: TranslationEntry, source_path: Path
    ) -> InsertResult:
        """Insert translation into database array data (Actors.json, etc.).

        Args:
            data: The database JSON array.
            entry: The translation entry.
            source_path: Path to the source file.

        Returns:
            InsertResult indicating the outcome.
        """
        if not isinstance(data, list):
            issue = InsertIssue(
                severity="error",
                code="invalid_structure",
                message="Database file must be an array",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        metadata = entry.metadata or {}
        item_id = metadata.get("item_id")
        field_name = metadata.get("field")

        if item_id is None or field_name is None:
            issue = InsertIssue(
                severity="error",
                code="invalid_location",
                message="Missing item_id or field in metadata",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.INVALID_LOCATION,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Find the item by ID
        for item in data:
            if not isinstance(item, dict):
                continue
            if item.get("id") == item_id:
                if field_name not in item:
                    issue = InsertIssue(
                        severity="error",
                        code="field_not_found",
                        message=f"Field '{field_name}' not found in item {item_id}",
                        entry_id=entry.id,
                        source_file=source_path,
                    )
                    return InsertResult(
                        entry_id=entry.id,
                        status=InsertStatus.NOT_FOUND,
                        original_text=entry.original_text,
                        source_file=source_path,
                        issues=(issue,),
                    )

                return self._validate_and_set(item, field_name, entry, source_path)

        issue = InsertIssue(
            severity="error",
            code="item_not_found",
            message=f"Item with id {item_id} not found",
            entry_id=entry.id,
            source_file=source_path,
        )
        return InsertResult(
            entry_id=entry.id,
            status=InsertStatus.NOT_FOUND,
            original_text=entry.original_text,
            source_file=source_path,
            issues=(issue,),
        )

    def _insert_common_event(
        self, data: Any, entry: TranslationEntry, source_path: Path
    ) -> InsertResult:
        """Insert translation into CommonEvents.json data.

        Args:
            data: The CommonEvents.json array.
            entry: The translation entry.
            source_path: Path to the source file.

        Returns:
            InsertResult indicating the outcome.
        """
        # Common events are handled like other database arrays
        return self._insert_database(data, entry, source_path)

    def _insert_map(
        self, data: Any, entry: TranslationEntry, source_path: Path
    ) -> InsertResult:
        """Insert translation into MapXXX.json data.

        Args:
            data: The Map JSON structure.
            entry: The translation entry.
            source_path: Path to the source file.

        Returns:
            InsertResult indicating the outcome.
        """
        if not isinstance(data, dict):
            issue = InsertIssue(
                severity="error",
                code="invalid_structure",
                message="Map file must be a dictionary",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        metadata = entry.metadata or {}
        field_name = metadata.get("field", "")

        # Handle map displayName
        if field_name == "displayName":
            return self._validate_and_set(data, "displayName", entry, source_path)

        # Handle event name
        if field_name == "name" and "event_id" in metadata:
            event_id = metadata["event_id"]
            events = data.get("events", [])
            if isinstance(events, list):
                for event in events:
                    if isinstance(event, dict) and event.get("id") == event_id:
                        return self._validate_and_set(event, "name", entry, source_path)

        # Handle event commands (Show Text, Show Choices)
        if "event_id" in metadata and "page" in metadata:
            return self._insert_map_command(data, entry, source_path)

        issue = InsertIssue(
            severity="error",
            code="field_not_found",
            message=f"Cannot locate field in map: {field_name}",
            entry_id=entry.id,
            source_file=source_path,
        )
        return InsertResult(
            entry_id=entry.id,
            status=InsertStatus.NOT_FOUND,
            original_text=entry.original_text,
            source_file=source_path,
            issues=(issue,),
        )

    def _insert_map_command(
        self, data: Any, entry: TranslationEntry, source_path: Path
    ) -> InsertResult:
        """Insert translation into a map event command.

        Args:
            data: The Map JSON structure.
            entry: The translation entry.
            source_path: Path to the source file.

        Returns:
            InsertResult indicating the outcome.
        """
        metadata = entry.metadata or {}
        event_id = metadata.get("event_id")
        page = metadata.get("page")
        field_name = metadata.get("field", "")
        command_code = metadata.get("command_code")

        if event_id is None or page is None:
            issue = InsertIssue(
                severity="error",
                code="invalid_location",
                message="Missing event_id or page in metadata",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.INVALID_LOCATION,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Find the event
        events = data.get("events", [])
        if not isinstance(events, list):
            issue = InsertIssue(
                severity="error",
                code="invalid_structure",
                message="Map events must be an array",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        event = None
        for e in events:
            if isinstance(e, dict) and e.get("id") == event_id:
                event = e
                break

        if event is None:
            issue = InsertIssue(
                severity="error",
                code="event_not_found",
                message=f"Event {event_id} not found",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.NOT_FOUND,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Find the page
        pages = event.get("pages", [])
        if not isinstance(pages, list) or page > len(pages):
            issue = InsertIssue(
                severity="error",
                code="page_not_found",
                message=f"Page {page} not found in event {event_id}",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.NOT_FOUND,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        target_page = pages[page - 1]  # Pages are 1-indexed
        if not isinstance(target_page, dict):
            issue = InsertIssue(
                severity="error",
                code="invalid_structure",
                message=f"Page {page} is not a dictionary",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Get the command list
        command_list = target_page.get("list", [])
        if not isinstance(command_list, list):
            issue = InsertIssue(
                severity="error",
                code="invalid_structure",
                message=f"Command list on page {page} is not an array",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Parse entry_id to find command index
        # Format: map:Map001:event:1:cmd:5:text or map:Map001:event:1:cmd:3:choice:0
        entry_parts = entry.id.split(":")
        try:
            cmd_idx = None
            choice_idx = None

            for i, part in enumerate(entry_parts):
                if part == "cmd" and i + 1 < len(entry_parts):
                    cmd_idx = int(entry_parts[i + 1])
                if part == "choice" and i + 1 < len(entry_parts):
                    choice_idx = int(entry_parts[i + 1])

            if cmd_idx is None or cmd_idx >= len(command_list):
                raise IndexError("Command index out of range")

        except (ValueError, IndexError):
            issue = InsertIssue(
                severity="error",
                code="invalid_location",
                message="Cannot parse command index from entry_id",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.INVALID_LOCATION,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        cmd = command_list[cmd_idx]
        if not isinstance(cmd, dict):
            issue = InsertIssue(
                severity="error",
                code="invalid_structure",
                message=f"Command at index {cmd_idx} is not a dictionary",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Handle Show Text (code 101/401)
        if command_code == 101:
            return self._insert_show_text(
                command_list, cmd_idx, entry, source_path
            )
        elif command_code == 102:
            # Handle Show Choices
            return self._insert_show_choice(
                command_list, cmd_idx, choice_idx, entry, source_path
            )

        issue = InsertIssue(
            severity="error",
            code="unsupported_command",
            message=f"Unsupported command code: {command_code}",
            entry_id=entry.id,
            source_file=source_path,
        )
        return InsertResult(
            entry_id=entry.id,
            status=InsertStatus.FAILED,
            original_text=entry.original_text,
            source_file=source_path,
            issues=(issue,),
        )

    def _insert_show_text(
        self,
        command_list: list,
        cmd_idx: int,
        entry: TranslationEntry,
        source_path: Path,
    ) -> InsertResult:
        """Insert translation for a Show Text command.

        Args:
            command_list: The event command list.
            cmd_idx: Index of the Show Text command.
            entry: The translation entry.
            source_path: Path to the source file.

        Returns:
            InsertResult indicating the outcome.
        """
        cmd = command_list[cmd_idx]
        parameters = cmd.get("parameters", [])

        if not parameters or len(parameters) < 1:
            issue = InsertIssue(
                severity="error",
                code="invalid_command",
                message="Show Text command has no parameters",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        original_value = parameters[0]
        if not isinstance(original_value, str):
            issue = InsertIssue(
                severity="error",
                code="invalid_type",
                message="Show Text parameter is not a string",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Validate original text matches
        if original_value != entry.original_text:
            issue = InsertIssue(
                severity="error",
                code="mismatch",
                message=f"Original text mismatch. Expected: '{entry.original_text}', Found: '{original_value}'",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.MISMATCH,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Apply translation
        command_list[cmd_idx]["parameters"][0] = entry.translated_text or ""

        # Handle continuation commands (401)
        if "\n" in entry.translated_text:
            lines = entry.translated_text.split("\n")
            # Remove existing continuation commands
            next_idx = cmd_idx + 1
            while next_idx < len(command_list):
                next_cmd = command_list[next_idx]
                if isinstance(next_cmd, dict) and next_cmd.get("code") == 401:
                    command_list.pop(next_idx)
                else:
                    break

            # Add continuation commands for additional lines
            for i, line in enumerate(lines[1:], start=1):
                continuation_cmd = {
                    "code": 401,
                    "indent": cmd.get("indent", 0),
                    "parameters": [line],
                }
                command_list.insert(cmd_idx + i, continuation_cmd)
        else:
            # Single line - remove any existing continuations
            next_idx = cmd_idx + 1
            while next_idx < len(command_list):
                next_cmd = command_list[next_idx]
                if isinstance(next_cmd, dict) and next_cmd.get("code") == 401:
                    command_list.pop(next_idx)
                else:
                    break

        return InsertResult(
            entry_id=entry.id,
            status=InsertStatus.SUCCESS,
            original_text=entry.original_text,
            translated_text=entry.translated_text,
            source_file=source_path,
        )

    def _insert_show_choice(
        self,
        command_list: list,
        cmd_idx: int,
        choice_idx: int | None,
        entry: TranslationEntry,
        source_path: Path,
    ) -> InsertResult:
        """Insert translation for a Show Choices command.

        Args:
            command_list: The event command list.
            cmd_idx: Index of the Show Choices command.
            choice_idx: Index of the specific choice to translate.
            entry: The translation entry.
            source_path: Path to the source file.

        Returns:
            InsertResult indicating the outcome.
        """
        if choice_idx is None:
            issue = InsertIssue(
                severity="error",
                code="invalid_location",
                message="choice_idx required for Show Choices",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.INVALID_LOCATION,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        cmd = command_list[cmd_idx]
        parameters = cmd.get("parameters", [])

        if not parameters or len(parameters) < 1:
            issue = InsertIssue(
                severity="error",
                code="invalid_command",
                message="Show Choices command has no parameters",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        choices = parameters[0]
        if not isinstance(choices, list) or choice_idx >= len(choices):
            issue = InsertIssue(
                severity="error",
                code="invalid_index",
                message=f"Choice index {choice_idx} out of range",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        original_value = choices[choice_idx]
        if not isinstance(original_value, str):
            issue = InsertIssue(
                severity="error",
                code="invalid_type",
                message="Choice value is not a string",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Validate original text matches
        if original_value != entry.original_text:
            issue = InsertIssue(
                severity="error",
                code="mismatch",
                message=f"Original text mismatch. Expected: '{entry.original_text}', Found: '{original_value}'",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.MISMATCH,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Apply translation
        command_list[cmd_idx]["parameters"][0][choice_idx] = (
            entry.translated_text or ""
        )

        return InsertResult(
            entry_id=entry.id,
            status=InsertStatus.SUCCESS,
            original_text=entry.original_text,
            translated_text=entry.translated_text,
            source_file=source_path,
        )

    def _validate_and_set(
        self,
        data: dict,
        field_name: str,
        entry: TranslationEntry,
        source_path: Path,
        nested_field: str | None = None,
    ) -> InsertResult:
        """Validate original text and set translated text.

        Args:
            data: The dictionary containing the field.
            field_name: The name of the field to update.
            entry: The translation entry.
            source_path: Path to the source file.
            nested_field: Optional nested field within the main field.

        Returns:
            InsertResult indicating the outcome.
        """
        if field_name not in data:
            issue = InsertIssue(
                severity="error",
                code="field_not_found",
                message=f"Field '{field_name}' not found",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.NOT_FOUND,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        original_value = data[field_name]
        if nested_field:
            if not isinstance(original_value, dict):
                issue = InsertIssue(
                    severity="error",
                    code="invalid_type",
                    message=f"Field '{field_name}' is not a dictionary",
                    entry_id=entry.id,
                    source_file=source_path,
                )
                return InsertResult(
                    entry_id=entry.id,
                    status=InsertStatus.FAILED,
                    original_text=entry.original_text,
                    source_file=source_path,
                    issues=(issue,),
                )
            if nested_field not in original_value:
                issue = InsertIssue(
                    severity="error",
                    code="field_not_found",
                    message=f"Nested field '{nested_field}' not found",
                    entry_id=entry.id,
                    source_file=source_path,
                )
                return InsertResult(
                    entry_id=entry.id,
                    status=InsertStatus.NOT_FOUND,
                    original_text=entry.original_text,
                    source_file=source_path,
                    issues=(issue,),
                )
            original_value = original_value[nested_field]

        if not isinstance(original_value, str):
            issue = InsertIssue(
                severity="error",
                code="invalid_type",
                message=f"Field '{field_name}' is not a string",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.FAILED,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Validate original text matches
        if original_value != entry.original_text:
            issue = InsertIssue(
                severity="error",
                code="mismatch",
                message=f"Original text mismatch. Expected: '{entry.original_text}', Found: '{original_value}'",
                entry_id=entry.id,
                source_file=source_path,
            )
            return InsertResult(
                entry_id=entry.id,
                status=InsertStatus.MISMATCH,
                original_text=entry.original_text,
                source_file=source_path,
                issues=(issue,),
            )

        # Apply translation
        if nested_field:
            data[field_name][nested_field] = entry.translated_text or ""
        else:
            data[field_name] = entry.translated_text or ""

        return InsertResult(
            entry_id=entry.id,
            status=InsertStatus.SUCCESS,
            original_text=entry.original_text,
            translated_text=entry.translated_text,
            source_file=source_path,
        )

    def _write_file(self, source_path: Path, data: Any) -> None:
        """Write modified data to the output path.

        Args:
            source_path: The original source file path.
            data: The modified JSON data.
        """
        # Calculate output path
        rel_path = source_path.relative_to(self.project_path)
        output_file = self.output_path / rel_path

        # Create parent directories if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON with consistent formatting
        content = json.dumps(data, ensure_ascii=False, indent=2)
        output_file.write_text(content, encoding="utf-8")
