"""Plugin interface definitions for RPG Translator Suite."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from app.core.detection import (
    ConfidenceLevel,
    DetectionEvidence,
    DetectionResult,
    DetectionStatus,
)
from app.core.project_model import ProjectStructureSpec


class BasePlugin(ABC):
    """Base class for all engine plugins.

    Sprint 0.1 defines only plugin identity and project detection. Feature
    methods such as extraction, translation import, validation, and patch
    generation are intentionally left for future sprints.

    Sprint 0.3 adds the ability for plugins to describe expected project structure
    in an engine-independent way via ProjectStructureSpec.
    """

    plugin_id: ClassVar[str]
    display_name: ClassVar[str]

    @abstractmethod
    def detect(self, project_path: Path) -> bool:
        """Return whether this plugin supports the provided project path.

        Args:
            project_path: Candidate project directory.
        """

    def detect_project(self, project_path: Path) -> DetectionResult:
        """Return a structured engine detection result.

        Plugins may override this method to provide rich evidence. The default
        adapter preserves the Sprint 0.1 boolean detection contract.
        """
        if self.detect(project_path):
            return DetectionResult(
                status=DetectionStatus.INCOMPLETE,
                project_path=project_path,
                engine=self.plugin_id,
                display_name=self.display_name,
                confidence=ConfidenceLevel.LOW,
                evidence=(
                    DetectionEvidence(
                        path=project_path,
                        description=(
                            "Legacy boolean detect() returned True; no "
                            "structured engine evidence was provided."
                        ),
                        confidence_weight=0,
                    ),
                ),
                reason=(
                    "Legacy boolean detection matched, but structured "
                    "evidence is required to confirm the engine."
                ),
            )

        return DetectionResult(
            status=DetectionStatus.UNKNOWN,
            project_path=project_path,
            reason=f"{self.display_name} did not recognize this project.",
        )

    def describe_project_structure(
        self,
        project_path: Path,
        detection: DetectionResult,
    ) -> ProjectStructureSpec:
        """Describe the expected/relevant structure for this engine's projects.

        Plugins may override this method to declare what files and directories
        they expect or consider relevant for a given engine. The Core uses this
        information to validate and understand project layouts without knowing
        engine-specific details.

        This method is intentionally NOT a project loader. It only describes
        the expected structure; it does not read files, scan directories, or
        extract data from the project.

        Args:
            project_path: The candidate project directory path.
            detection: The detection result for this project.

        Returns:
            A ProjectStructureSpec describing expected/relevant structure.
            The default implementation returns an empty specification to
            maintain compatibility with plugins that do not yet implement
            this capability.

        Note:
            Plugins should override this method to provide engine-specific
            structure descriptions. The Core remains engine-independent by
            only knowing about the generic ProjectStructureSpec model.
        """
        return ProjectStructureSpec()
