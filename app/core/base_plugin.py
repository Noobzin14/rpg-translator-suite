"""Plugin interface definitions for RPG Translator Suite."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar


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
