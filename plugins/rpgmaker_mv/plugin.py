"""RPG Maker MV engine detection plugin."""

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
from app.core.project_model import (
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
            metadata={},
            expected_files=expected_files,
            expected_directories=expected_directories,
            relevant_files=relevant_files,
            relevant_directories=relevant_directories,
        )
