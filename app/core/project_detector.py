"""Project engine detection orchestration."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.detection import ConfidenceLevel, DetectionResult, DetectionStatus
from app.core.plugin_loader import PluginLoader

LOGGER = logging.getLogger(__name__)


class ProjectDetector:
    """Detect project engines by delegating engine-specific checks to plugins."""

    def __init__(self, plugin_loader: PluginLoader) -> None:
        """Initialize the detector with plugin loading infrastructure."""
        self._plugin_loader = plugin_loader

    def detect(self, project_path: Path) -> DetectionResult:
        """Detect the engine for a project directory without modifying it."""
        candidate_path = Path(project_path)
        if not candidate_path.exists() or not candidate_path.is_dir():
            return DetectionResult(
                status=DetectionStatus.INVALID_PATH,
                project_path=candidate_path,
                reason="Project path does not exist or is not a directory.",
            )

        detected_results: list[DetectionResult] = []
        for plugin in self._plugin_loader.load_registered_plugins():
            try:
                result = plugin.detect_project(candidate_path)
            except Exception as exc:  # pragma: no cover - defensive logging path
                LOGGER.exception(
                    "Plugin %s failed during project detection.",
                    plugin.plugin_id,
                )
                result = DetectionResult(
                    status=DetectionStatus.UNKNOWN,
                    project_path=candidate_path,
                    reason=f"Plugin {plugin.plugin_id} failed: {exc}",
                )
            if result.status == DetectionStatus.DETECTED:
                detected_results.append(result)

        if not detected_results:
            return DetectionResult(
                status=DetectionStatus.UNKNOWN,
                project_path=candidate_path,
                confidence=ConfidenceLevel.NONE,
                reason="No supported engine detected.",
            )

        if len(detected_results) > 1:
            return DetectionResult(
                status=DetectionStatus.CONFLICT,
                project_path=candidate_path,
                confidence=ConfidenceLevel.NONE,
                reason="Multiple engine detectors matched this project.",
                conflicts=tuple(detected_results),
            )

        return detected_results[0]
