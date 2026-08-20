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


class BasePlugin(ABC):
    """Base class for all engine plugins.

    Sprint 0.1 defines only plugin identity and project detection. Feature
    methods such as extraction, translation import, validation, and patch
    generation are intentionally left for future sprints.
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
