"""RPG Maker MV engine detection and data extraction plugin."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import ClassVar

from app.core.base_plugin import BasePlugin
from app.core.detection import (
    ConfidenceLevel,
    DetectionEvidence,
    DetectionResult,
    DetectionStatus,
)
from app.core.extraction import (
    ExtractionEntry,
    ExtractionEntryType,
    ExtractionIssue,
    ExtractionIssueSeverity,
    ExtractionResult,
    ExtractionStatus,
)
from app.core.project_model import (
    Project,
    ProjectFileKind,
    ProjectFileRole,
    ProjectFileSpec,
    ProjectStructureSpec,
)

_VERSION_PATTERN = re.compile(r"(?:RPG Maker MV|rpg_core\.js)\s+v?(\d+\.\d+\.\d+)", re.IGNORECASE)
_SIMPLE_VERSION_PATTERN = re.compile(r"\bv(\d+\.\d+\.\d+)\b")


class RPGMakerMVPlugin(BasePlugin):
    """Detect RPG Maker MV projects from characteristic project files."""

    plugin_id: ClassVar[str] = "rpgmaker_mv"
    display_name: ClassVar[str] = "RPG Maker MV"

    def detect(self, project_path: Path) -> bool:
        """Return whether the path contains enough MV evidence."""
        return self.detect_project(project_path).detected

    def detect_project(self, project_path: Path) -> DetectionResult:
        """Detect RPG Maker MV using read-only evidence inside the project."""
        evidence: list[DetectionEvidence] = []
        package_json = project_path / "package.json"
        system_json = project_path / "www" / "data" / "System.json"
        rpg_core = project_path / "www" / "js" / "rpg_core.js"

        package_mentions_core = self._package_mentions_rpg_core(package_json)
        if package_mentions_core:
            evidence.append(
                DetectionEvidence(
                    path=package_json,
                    description="package.json references rpg_core, a characteristic RPG Maker MV runtime file.",
                    confidence_weight=2,
                )
            )

        if system_json.is_file():
            evidence.append(
                DetectionEvidence(
                    path=system_json,
                    description="www/data/System.json exists, matching the RPG Maker MV data layout.",
                    confidence_weight=2,
                )
            )

        version = self._read_mv_version(rpg_core)
        if rpg_core.is_file():
            evidence.append(
                DetectionEvidence(
                    path=rpg_core,
                    description="www/js/rpg_core.js exists, matching the RPG Maker MV runtime layout.",
                    confidence_weight=3,
                )
            )

        score = sum(item.confidence_weight for item in evidence)
        if score >= 5:
            return DetectionResult(
                status=DetectionStatus.DETECTED,
                project_path=project_path,
                engine=self.plugin_id,
                display_name=self.display_name,
                version=version,
                confidence=ConfidenceLevel.HIGH if version else ConfidenceLevel.MEDIUM,
                evidence=tuple(evidence),
                reason=None if version else "Engine detected, but version could not be determined.",
            )

        if evidence:
            return DetectionResult(
                status=DetectionStatus.INCOMPLETE,
                project_path=project_path,
                engine=self.plugin_id,
                display_name=self.display_name,
                version=version,
                confidence=ConfidenceLevel.LOW,
                evidence=tuple(evidence),
                reason="RPG Maker MV evidence was found, but the project appears incomplete.",
            )

        return DetectionResult(
            status=DetectionStatus.UNKNOWN,
            project_path=project_path,
            confidence=ConfidenceLevel.NONE,
            reason="RPG Maker MV project evidence was not found.",
        )

    def _package_mentions_rpg_core(self, package_json: Path) -> bool:
        if not package_json.is_file():
            return False

        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False

        return "rpg_core" in json.dumps(data).lower()

    def _read_mv_version(self, rpg_core: Path) -> str | None:
        if not rpg_core.is_file():
            return None

        try:
            content = rpg_core.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None

        for pattern in (_VERSION_PATTERN, _SIMPLE_VERSION_PATTERN):
            match = pattern.search(content)
            if match:
                return match.group(1)
        return None

    def describe_project_structure(
        self,
        project_path: Path,
        detection: DetectionResult,
    ) -> ProjectStructureSpec:
        """Describe the expected/relevant structure for RPG Maker MV projects.

        This method declares the characteristic file/directory layout of an
        RPG Maker MV project using engine-independent models. The Core uses
        this information to validate and understand MV project layouts without
        knowing MV-specific details.

        Args:
            project_path: The candidate project directory path.
            detection: The detection result for this project.

        Returns:
            A ProjectStructureSpec describing expected/relevant MV structure.
        """
        # Build metadata from detection result and safe package.json reading
        metadata: dict[str, str | int | float | bool | None] = {}

        # Use engine information from DetectionResult (no duplication)
        if detection.display_name:
            metadata["engine_display_name"] = detection.display_name

        if detection.version:
            metadata["engine_version"] = detection.version

        # Safely read project_name from package.json if available
        package_json = project_path / "package.json"
        if package_json.is_file():
            try:
                # Read with size limit for safety (1MB max)
                content = package_json.read_text(encoding="utf-8")
                if len(content) > 1024 * 1024:
                    content = content[:1024 * 1024]
                data = json.loads(content)
                if isinstance(data, dict) and "name" in data:
                    name = data["name"]
                    if isinstance(name, str):
                        metadata["project_name"] = name
            except (OSError, json.JSONDecodeError):
                # Silently ignore errors - metadata failure should not break structure
                pass

        # Expected files - required for a valid MV project
        expected_files = (
            ProjectFileSpec(
                relative_path=Path("package.json"),
                kind=ProjectFileKind.FILE,
                role=ProjectFileRole.CONFIG,
                required=True,
                description="Package configuration file referencing rpg_core runtime.",
            ),
            ProjectFileSpec(
                relative_path=Path("www/data/System.json"),
                kind=ProjectFileKind.FILE,
                role=ProjectFileRole.DATA,
                required=True,
                description="System data file containing game configuration.",
            ),
        )

        # Expected directories - required structure
        expected_directories = (
            ProjectFileSpec(
                relative_path=Path("www"),
                kind=ProjectFileKind.DIRECTORY,
                role=ProjectFileRole.DATA,
                required=True,
                description="Root directory for web assets.",
            ),
            ProjectFileSpec(
                relative_path=Path("www/data"),
                kind=ProjectFileKind.DIRECTORY,
                role=ProjectFileRole.DATA,
                required=True,
                description="Directory containing game data JSON files.",
            ),
            ProjectFileSpec(
                relative_path=Path("www/js"),
                kind=ProjectFileKind.DIRECTORY,
                role=ProjectFileRole.SCRIPT,
                required=True,
                description="Directory containing JavaScript runtime files.",
            ),
        )

        # Relevant files - useful but not strictly required
        relevant_files = (
            ProjectFileSpec(
                relative_path=Path("www/js/rpg_core.js"),
                kind=ProjectFileKind.FILE,
                role=ProjectFileRole.SCRIPT,
                required=False,
                description="Main RPG Maker MV runtime library.",
            ),
        )

        # Relevant directories - useful but not strictly required
        relevant_directories: tuple[ProjectFileSpec, ...] = ()

        return ProjectStructureSpec(
            metadata=metadata,
            expected_files=expected_files,
            expected_directories=expected_directories,
            relevant_files=relevant_files,
            relevant_directories=relevant_directories,
        )

    def extract_data(self, project: Project) -> ExtractionResult:
        """Extract translatable data from an RPG Maker MV project.

        This implementation extracts all relevant textual content from:
        - System.json (game title and system texts)
        - package.json (project name)
        - Actors, Classes, Skills, Items, Weapons, Armors
        - Enemies, States, Animations, Tilesets, CommonEvents
        - Map*.json files (events, pages, show text, show choices)

        Args:
            project: The loaded RPG Maker MV project.

        Returns:
            An ExtractionResult containing extracted entries and any issues.
        """
        entries: list[ExtractionEntry] = []
        warnings: list[ExtractionIssue] = []
        errors: list[ExtractionIssue] = []

        project_path = project.path
        data_dir = project_path / "www" / "data"

        # Extract from database files
        self._extract_system_json(data_dir, entries, errors)
        self._extract_package_json(project_path, entries, warnings)
        
        # Extract database arrays
        self._extract_database_file(
            data_dir / "Actors.json", "actors", 
            [("name", ExtractionEntryType.NAME), ("nickname", ExtractionEntryType.NAME), 
             ("profile", ExtractionEntryType.DESCRIPTION)],
            entries, errors
        )
        self._extract_database_file(
            data_dir / "Classes.json", "classes",
            [("name", ExtractionEntryType.NAME)],
            entries, errors
        )
        self._extract_database_file(
            data_dir / "Skills.json", "skills",
            [("name", ExtractionEntryType.NAME), ("description", ExtractionEntryType.DESCRIPTION),
             ("message1", ExtractionEntryType.MESSAGE), ("message2", ExtractionEntryType.MESSAGE)],
            entries, errors
        )
        self._extract_database_file(
            data_dir / "Items.json", "items",
            [("name", ExtractionEntryType.NAME), ("description", ExtractionEntryType.DESCRIPTION)],
            entries, errors
        )
        self._extract_database_file(
            data_dir / "Weapons.json", "weapons",
            [("name", ExtractionEntryType.NAME), ("description", ExtractionEntryType.DESCRIPTION)],
            entries, errors
        )
        self._extract_database_file(
            data_dir / "Armors.json", "armors",
            [("name", ExtractionEntryType.NAME), ("description", ExtractionEntryType.DESCRIPTION)],
            entries, errors
        )
        self._extract_database_file(
            data_dir / "Enemies.json", "enemies",
            [("name", ExtractionEntryType.NAME)],
            entries, errors
        )
        self._extract_database_file(
            data_dir / "States.json", "states",
            [("name", ExtractionEntryType.NAME), ("message1", ExtractionEntryType.MESSAGE),
             ("message2", ExtractionEntryType.MESSAGE), ("message3", ExtractionEntryType.MESSAGE),
             ("message4", ExtractionEntryType.MESSAGE)],
            entries, errors
        )
        self._extract_database_file(
            data_dir / "Animations.json", "animations",
            [("name", ExtractionEntryType.NAME)],
            entries, errors
        )
        self._extract_database_file(
            data_dir / "Tilesets.json", "tilesets",
            [("name", ExtractionEntryType.NAME)],
            entries, errors
        )
        self._extract_database_file(
            data_dir / "CommonEvents.json", "commonEvents",
            [("name", ExtractionEntryType.NAME)],
            entries, errors,
            extract_event_commands=True
        )

        # Extract from map files
        self._extract_map_files(data_dir, entries, errors)

        # Determine status based on results
        if errors:
            status = ExtractionStatus.READ_ERROR if not entries else ExtractionStatus.PARTIAL
        elif entries:
            status = ExtractionStatus.EXTRACTED
        else:
            status = ExtractionStatus.PARTIAL

        return ExtractionResult(
            status=status,
            entries=tuple(entries),
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    def _extract_system_json(
        self, data_dir: Path, entries: list[ExtractionEntry], errors: list[ExtractionIssue]
    ) -> None:
        """Extract translatable fields from System.json."""
        system_json_path = data_dir / "System.json"
        if not system_json_path.is_file():
            errors.append(
                ExtractionIssue(
                    severity=ExtractionIssueSeverity.ERROR,
                    code="missing_file",
                    message="System.json not found; game title cannot be extracted.",
                    path=Path("www/data/System.json"),
                )
            )
            return
        
        try:
            content = system_json_path.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, dict):
                return
            
            # Extract gameTitle
            if "gameTitle" in data and isinstance(data["gameTitle"], str) and data["gameTitle"].strip():
                entries.append(
                    ExtractionEntry(
                        entry_id="system:game_title",
                        entry_type=ExtractionEntryType.NAME,
                        text=data["gameTitle"],
                        source_path=Path("www/data/System.json"),
                        metadata={"source_kind": "system", "field": "gameTitle"},
                    )
                )
            
            # Extract terms (if present)
            terms = data.get("terms", {})
            if isinstance(terms, dict):
                term_fields = [
                    ("basic", ["party"]),
                    ("params", ["hp", "mp", "tp", "exp", "level", "money"]),
                    ("commands", ["fight", "escape", "attack", "guard", "item", "skill", 
                                  "equip", "status", "formation", "save", "gameEnd", 
                                  "options", "weapon", "armor", "keyItem"]),
                    ("messages", ["levelUp", "obtainedExp", "obtainedGold", "obtainedItem",
                                  "obtainedKeyItem", "acting", "substitute", "criticalHit",
                                  "actorDamage", "actorRecovery", "enemyDamage", "enemyRecovery",
                                  "actorDrain", "enemyDrain", "miss", "evasion", "counterAttack",
                                  "noDamage", "weakness", "break", "noEffect", "notEnoughMoney",
                                  "hpCost", "mpCost", "buffActivate", "debuffActivate",
                                  "damageReduced", "reflectSpell", "counterAttackBy",
                                  "followUpAttack", "skillAffected", "affectedByState",
                                  "stateRecovery", "stateAdded", "stateRemoved", "actionFailure"]),
                ]
                for category, fields in term_fields:
                    if category in terms and isinstance(terms[category], dict):
                        for field in fields:
                            if field in terms[category] and isinstance(terms[category][field], str):
                                val = terms[category][field].strip()
                                if val:
                                    entries.append(
                                        ExtractionEntry(
                                            entry_id=f"system:terms:{category}:{field}",
                                            entry_type=ExtractionEntryType.NAME,
                                            text=val,
                                            source_path=Path("www/data/System.json"),
                                            metadata={"source_kind": "system", "category": category, "field": field},
                                        )
                                    )
            
            # Extract vehicle names
            vehicles = data.get("vehicles", [])
            if isinstance(vehicles, list):
                for i, vehicle in enumerate(vehicles):
                    if isinstance(vehicle, dict) and "name" in vehicle:
                        name = vehicle["name"]
                        if isinstance(name, str) and name.strip():
                            entries.append(
                                ExtractionEntry(
                                    entry_id=f"system:vehicle:{i}:name",
                                    entry_type=ExtractionEntryType.NAME,
                                    text=name,
                                    source_path=Path("www/data/System.json"),
                                    metadata={"source_kind": "system", "field": f"vehicles[{i}].name"},
                                )
                            )
                            
        except json.JSONDecodeError as exc:
            errors.append(
                ExtractionIssue(
                    severity=ExtractionIssueSeverity.ERROR,
                    code="invalid_json",
                    message=f"Failed to parse System.json: {exc}",
                    path=Path("www/data/System.json"),
                )
            )
        except OSError as exc:
            errors.append(
                ExtractionIssue(
                    severity=ExtractionIssueSeverity.ERROR,
                    code="read_error",
                    message=f"Failed to read System.json: {exc}",
                    path=Path("www/data/System.json"),
                )
            )

    def _extract_package_json(
        self, project_path: Path, entries: list[ExtractionEntry], warnings: list[ExtractionIssue]
    ) -> None:
        """Extract project name from package.json."""
        package_json_path = project_path / "package.json"
        if not package_json_path.is_file():
            return
        
        try:
            content = package_json_path.read_text(encoding="utf-8")
            if len(content) > 1024 * 1024:
                content = content[: 1024 * 1024]
            data = json.loads(content)
            if isinstance(data, dict) and "name" in data:
                project_name = data["name"]
                if isinstance(project_name, str) and project_name.strip():
                    entries.append(
                        ExtractionEntry(
                            entry_id="system:project_name",
                            entry_type=ExtractionEntryType.NAME,
                            text=project_name,
                            source_path=Path("package.json"),
                            metadata={"source_kind": "config", "field": "name"},
                        )
                    )
        except json.JSONDecodeError as exc:
            warnings.append(
                ExtractionIssue(
                    severity=ExtractionIssueSeverity.WARNING,
                    code="invalid_json",
                    message=f"Failed to parse package.json: {exc}",
                    path=Path("package.json"),
                )
            )
        except OSError as exc:
            warnings.append(
                ExtractionIssue(
                    severity=ExtractionIssueSeverity.WARNING,
                    code="read_error",
                    message=f"Failed to read package.json: {exc}",
                    path=Path("package.json"),
                )
            )

    def _extract_database_file(
        self,
        file_path: Path,
        array_name: str,
        fields: list[tuple[str, ExtractionEntryType]],
        entries: list[ExtractionEntry],
        errors: list[ExtractionIssue],
        extract_event_commands: bool = False,
    ) -> None:
        """Extract translatable text from a database JSON file.
        
        Args:
            file_path: Path to the JSON file.
            array_name: Name of the array in the JSON (e.g., 'actors').
            fields: List of (field_name, entry_type) tuples to extract.
            entries: List to append extracted entries to.
            errors: List to append errors to.
            extract_event_commands: Whether to extract event command texts.
        """
        if not file_path.is_file():
            return
        
        rel_path = Path(f"www/data/{file_path.name}")
        
        try:
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, list):
                return
            
            for item in data:
                if not isinstance(item, dict):
                    continue
                
                item_id = item.get("id")
                if item_id is None:
                    continue
                
                # Extract specified fields
                for field_name, entry_type in fields:
                    if field_name in item and isinstance(item[field_name], str):
                        text = item[field_name].strip()
                        if text:
                            entries.append(
                                ExtractionEntry(
                                    entry_id=f"{array_name}:{item_id}:{field_name}",
                                    entry_type=entry_type,
                                    text=text,
                                    source_path=rel_path,
                                    metadata={
                                        "source_kind": array_name.rstrip('s'),
                                        "item_id": item_id,
                                        "field": field_name,
                                    },
                                )
                            )
                
                # Extract event commands if requested (for commonEvents)
                if extract_event_commands and "list" in item and isinstance(item["list"], list):
                    self._extract_event_commands(
                        item["list"], entries, rel_path, 
                        {"source_kind": array_name.rstrip('s'), "item_id": item_id}
                    )
                    
        except json.JSONDecodeError as exc:
            errors.append(
                ExtractionIssue(
                    severity=ExtractionIssueSeverity.ERROR,
                    code="invalid_json",
                    message=f"Failed to parse {file_path.name}: {exc}",
                    path=rel_path,
                )
            )
        except OSError as exc:
            errors.append(
                ExtractionIssue(
                    severity=ExtractionIssueSeverity.ERROR,
                    code="read_error",
                    message=f"Failed to read {file_path.name}: {exc}",
                    path=rel_path,
                )
            )

    def _extract_map_files(
        self, data_dir: Path, entries: list[ExtractionEntry], errors: list[ExtractionIssue]
    ) -> None:
        """Extract translatable text from all Map*.json files."""
        if not data_dir.is_dir():
            return
        
        # Find all Map*.json files
        map_files = sorted(data_dir.glob("Map*.json"))
        
        for map_file in map_files:
            # Skip System.json and other non-map files
            if map_file.name == "System.json":
                continue
            
            rel_path = Path(f"www/data/{map_file.name}")
            
            try:
                content = map_file.read_text(encoding="utf-8")
                data = json.loads(content)
                if not isinstance(data, dict):
                    continue
                
                # Extract map name
                if "displayName" in data and isinstance(data["displayName"], str):
                    name = data["displayName"].strip()
                    if name:
                        entries.append(
                            ExtractionEntry(
                                entry_id=f"map:{map_file.stem}:displayName",
                                entry_type=ExtractionEntryType.NAME,
                                text=name,
                                source_path=rel_path,
                                metadata={"source_kind": "map", "field": "displayName"},
                            )
                        )
                
                # Extract events
                events = data.get("events", [])
                if isinstance(events, list):
                    for event in events:
                        if not isinstance(event, dict):
                            continue
                        
                        event_id = event.get("id")
                        if event_id is None:
                            continue
                        
                        # Extract event name
                        if "name" in event and isinstance(event["name"], str):
                            name = event["name"].strip()
                            if name:
                                entries.append(
                                    ExtractionEntry(
                                        entry_id=f"map:{map_file.stem}:event:{event_id}:name",
                                        entry_type=ExtractionEntryType.NAME,
                                        text=name,
                                        source_path=rel_path,
                                        metadata={
                                            "source_kind": "map",
                                            "map": map_file.stem,
                                            "event_id": event_id,
                                            "field": "name",
                                        },
                                    )
                                )
                        
                        # Extract pages
                        pages = event.get("pages", [])
                        if isinstance(pages, list):
                            for page_idx, page in enumerate(pages):
                                if not isinstance(page, dict):
                                    continue
                                
                                # Extract event commands from page list
                                page_list = page.get("list", [])
                                if isinstance(page_list, list) and page_list:
                                    self._extract_event_commands(
                                        page_list, entries, rel_path,
                                        {
                                            "source_kind": "map",
                                            "map": map_file.stem,
                                            "event_id": event_id,
                                            "page": page_idx + 1,
                                        }
                                    )
                                    
            except json.JSONDecodeError as exc:
                errors.append(
                    ExtractionIssue(
                        severity=ExtractionIssueSeverity.ERROR,
                        code="invalid_json",
                        message=f"Failed to parse {map_file.name}: {exc}",
                        path=rel_path,
                    )
                )
            except OSError as exc:
                errors.append(
                    ExtractionIssue(
                        severity=ExtractionIssueSeverity.ERROR,
                        code="read_error",
                        message=f"Failed to read {map_file.name}: {exc}",
                        path=rel_path,
                    )
                )

    def _extract_event_commands(
        self,
        command_list: list,
        entries: list[ExtractionEntry],
        source_path: Path,
        base_metadata: dict,
    ) -> None:
        """Extract text from RPG Maker MV event commands.
        
        Handles:
        - Command 101: Show Text
        - Command 102: Show Choices
        - Command 401: Show Text (continuation)
        
        Args:
            command_list: List of event commands.
            entries: List to append extracted entries to.
            source_path: Relative path to the source file.
            base_metadata: Base metadata dictionary for entries.
        """
        if not isinstance(command_list, list):
            return
        
        current_text_lines: list[str] = []
        current_command_index: int | None = None
        
        for cmd_idx, cmd in enumerate(command_list):
            if not isinstance(cmd, dict):
                continue
            
            code = cmd.get("code")
            parameters = cmd.get("parameters", [])
            
            if code == 101:
                # Show Text - start new text block
                if current_text_lines and current_command_index is not None:
                    # Save previous text block
                    self._add_event_text_entry(
                        current_text_lines, entries, source_path, base_metadata, current_command_index
                    )
                
                current_text_lines = []
                current_command_index = cmd_idx
                
                # First line of text is in parameters[0]
                if parameters and len(parameters) > 0 and isinstance(parameters[0], str):
                    text = parameters[0].strip()
                    if text:
                        current_text_lines.append(text)
                
                # Check for speaker name in parameters[4] (MV format)
                if len(parameters) > 4 and isinstance(parameters[4], str):
                    speaker = parameters[4].strip()
                    if speaker:
                        # Add speaker as separate entry
                        entries.append(
                            ExtractionEntry(
                                entry_id=f"map:{base_metadata.get('map', 'unknown')}:event:{base_metadata.get('event_id', 0)}:cmd:{cmd_idx}:speaker",
                                entry_type=ExtractionEntryType.NAME,
                                text=speaker,
                                source_path=source_path,
                                metadata={
                                    **base_metadata,
                                    "field": "speaker",
                                    "command_code": 101,
                                },
                            )
                        )
                        
            elif code == 401:
                # Show Text continuation
                if parameters and len(parameters) > 0 and isinstance(parameters[0], str):
                    text = parameters[0].strip()
                    if text:
                        current_text_lines.append(text)
                        
            elif code == 102:
                # Show Choices - save any pending text first
                if current_text_lines and current_command_index is not None:
                    self._add_event_text_entry(
                        current_text_lines, entries, source_path, base_metadata, current_command_index
                    )
                    current_text_lines = []
                    current_command_index = None
                
                # Extract choices
                if parameters and len(parameters) > 0 and isinstance(parameters[0], list):
                    choices = parameters[0]
                    for choice_idx, choice in enumerate(choices):
                        if isinstance(choice, str) and choice.strip():
                            entries.append(
                                ExtractionEntry(
                                    entry_id=f"map:{base_metadata.get('map', 'unknown')}:event:{base_metadata.get('event_id', 0)}:cmd:{cmd_idx}:choice:{choice_idx}",
                                    entry_type=ExtractionEntryType.NAME,
                                    text=choice.strip(),
                                    source_path=source_path,
                                    metadata={
                                        **base_metadata,
                                        "field": f"choice[{choice_idx}]",
                                        "command_code": 102,
                                    },
                                )
                            )
                            
            elif code == 404:
                # End of choices - nothing to extract
                
                pass
            else:
                # Other command - save any pending text
                if current_text_lines and current_command_index is not None:
                    self._add_event_text_entry(
                        current_text_lines, entries, source_path, base_metadata, current_command_index
                    )
                    current_text_lines = []
                    current_command_index = None
        
        # Save any remaining text
        if current_text_lines and current_command_index is not None:
            self._add_event_text_entry(
                current_text_lines, entries, source_path, base_metadata, current_command_index
            )

    def _add_event_text_entry(
        self,
        text_lines: list[str],
        entries: list[ExtractionEntry],
        source_path: Path,
        base_metadata: dict,
        command_index: int,
    ) -> None:
        """Add an extraction entry for event text.
        
        Args:
            text_lines: List of text lines to join.
            entries: List to append the entry to.
            source_path: Relative path to the source file.
            base_metadata: Base metadata dictionary.
            command_index: Index of the command in the event list.
        """
        full_text = "\n".join(text_lines)
        if not full_text.strip():
            return
        
        map_ref = base_metadata.get('map', 'unknown')
        event_ref = base_metadata.get('event_id', 0)
        
        entries.append(
            ExtractionEntry(
                entry_id=f"map:{map_ref}:event:{event_ref}:cmd:{command_index}:text",
                entry_type=ExtractionEntryType.MESSAGE,
                text=full_text,
                source_path=source_path,
                metadata={
                    **base_metadata,
                    "field": "text",
                    "command_code": 101,
                },
            )
        )
