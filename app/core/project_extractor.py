"""Project extraction orchestration for RPG Translator Suite."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.base_plugin import BasePlugin
from app.core.extraction import (
    ExtractionIssue,
    ExtractionIssueSeverity,
    ExtractionResult,
    ExtractionStatus,
)
from app.core.plugin_manager import PluginManager
from app.core.project_model import Project, ProjectLoadStatus

logger = logging.getLogger(__name__)


class ProjectExtractor:
    """Coordinates data extraction from loaded projects.

    The ProjectExtractor receives a Project and orchestrates extraction by:
    1. Verifying the project is in a valid state for extraction
    2. Resolving the appropriate plugin based on the project's engine
    3. Delegating extraction to the plugin
    4. Handling errors and returning structured results

    The Core remains engine-independent by only knowing about generic
    extraction models. Engine-specific extraction logic belongs in plugins.
    """

    def __init__(self, plugin_manager: PluginManager) -> None:
        """Initialize the extractor with a plugin manager.

        Args:
            plugin_manager: Manager for resolving engine plugins.
        """
        self._plugin_manager = plugin_manager

    def extract(self, project: Project) -> ExtractionResult:
        """Extract translatable data from a project.

        This method coordinates the extraction process:
        1. Validates the project state
        2. Resolves the appropriate plugin by engine
        3. Delegates extraction to the plugin
        4. Handles exceptions and returns structured results

        Args:
            project: The loaded project to extract data from.

        Returns:
            An ExtractionResult containing extracted entries and any issues.
        """
        # Validate project state before extraction
        if project.status != ProjectLoadStatus.LOADED:
            return ExtractionResult(
                status=ExtractionStatus.INVALID_PROJECT,
                errors=(
                    ExtractionIssue(
                        severity=ExtractionIssueSeverity.ERROR,
                        code="invalid_project_state",
                        message=(
                            f"Project is not in LOADED state. "
                            f"Current status: {project.status.value}"
                        ),
                        path=project.path,
                    ),
                ),
                project=project,
            )

        # Resolve plugin by engine
        if not project.engine:
            return ExtractionResult(
                status=ExtractionStatus.NOT_SUPPORTED,
                errors=(
                    ExtractionIssue(
                        severity=ExtractionIssueSeverity.ERROR,
                        code="unknown_engine",
                        message="Project has no associated engine.",
                        path=project.path,
                    ),
                ),
                project=project,
            )

        plugin = self._plugin_manager.get(project.engine)
        if plugin is None:
            return ExtractionResult(
                status=ExtractionStatus.NOT_SUPPORTED,
                errors=(
                    ExtractionIssue(
                        severity=ExtractionIssueSeverity.ERROR,
                        code="plugin_not_found",
                        message=f"No plugin found for engine: {project.engine}",
                        path=project.path,
                    ),
                ),
                project=project,
            )

        # Delegate extraction to plugin
        try:
            result = plugin.extract_data(project)
            # Attach project reference if not already present
            if result.project is None:
                # Need to create a new result with project attached
                # since ExtractionResult is frozen
                result = ExtractionResult(
                    status=result.status,
                    entries=result.entries,
                    warnings=result.warnings,
                    errors=result.errors,
                    project=project,
                )
            return result
        except Exception as exc:
            logger.exception(
                "Unexpected error during extraction for project %s using plugin %s",
                project.path,
                project.engine,
            )
            return ExtractionResult(
                status=ExtractionStatus.FAILED,
                errors=(
                    ExtractionIssue(
                        severity=ExtractionIssueSeverity.ERROR,
                        code="extraction_failed",
                        message=f"Unexpected error during extraction: {exc}",
                        path=project.path,
                    ),
                ),
                project=project,
            )
