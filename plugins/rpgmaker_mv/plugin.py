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

        This implementation performs minimal extraction to demonstrate the API:
        - Game title from System.json
        - Project name from package.json

        Full extraction of maps, events, actors, skills, items, etc. is left
        for future stages.

        Args:
            project: The loaded RPG Maker MV project.

        Returns:
            An ExtractionResult containing extracted entries and any issues.
        """
        entries: list[ExtractionEntry] = []
        warnings: list[ExtractionIssue] = []
        errors: list[ExtractionIssue] = []

        project_path = project.path

        # Extract game title from System.json
        system_json_path = project_path / "www" / "data" / "System.json"
        if system_json_path.is_file():
            try:
                content = system_json_path.read_text(encoding="utf-8")
                data = json.loads(content)
                if isinstance(data, dict) and "gameTitle" in data:
                    game_title = data["gameTitle"]
                    if isinstance(game_title, str) and game_title.strip():
                        entries.append(
                            ExtractionEntry(
                                entry_id="system:game_title",
                                entry_type=ExtractionEntryType.NAME,
                                text=game_title,
                                source_path=Path("www/data/System.json"),
                                metadata={"source_kind": "system", "field": "gameTitle"},
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
        else:
            warnings.append(
                ExtractionIssue(
                    severity=ExtractionIssueSeverity.WARNING,
                    code="missing_file",
                    message="System.json not found; game title cannot be extracted.",
                    path=Path("www/data/System.json"),
                )
            )

        # Extract project name from package.json (if available in metadata)
        package_json_path = project_path / "package.json"
        if package_json_path.is_file():
            try:
                content = package_json_path.read_text(encoding="utf-8")
                # Size limit for safety (1MB max)
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
