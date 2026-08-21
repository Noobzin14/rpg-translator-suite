"""Project loading orchestration for RPG Translator Suite."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.detection import DetectionResult, DetectionStatus
from app.core.plugin_manager import PluginManager
from app.core.project_detector import ProjectDetector
from app.core.project_model import (
    Project,
    ProjectFile,
    ProjectFileKind,
    ProjectFileRole,
    ProjectFileSpec,
    ProjectIssue,
    ProjectIssueSeverity,
    ProjectLoadResult,
    ProjectLoadStatus,
    ProjectMetadata,
    ProjectStructure,
    ProjectStructureSpec,
)

LOGGER = logging.getLogger(__name__)


class ProjectLoader:
    """Orchestrates project loading by coordinating detection and plugin structure APIs.

    The ProjectLoader is engine-independent. It does not contain knowledge of
    specific engines. Instead, it relies on plugins to provide engine-specific
    structure information through the ProjectStructureSpec API.

    Responsibilities:
        - Validate project path
        - Orchestrate detection via ProjectDetector
        - Resolve detected plugin via PluginManager
        - Consume ProjectStructureSpec from plugin
        - Validate filesystem against spec (generic validation)
        - Build ProjectFile / ProjectStructure / Project
        - Return ProjectLoadResult with appropriate status and issues
    """

    def __init__(
        self,
        detector: ProjectDetector,
        plugin_manager: PluginManager,
    ) -> None:
        """Initialize the ProjectLoader.

        Args:
            detector: ProjectDetector instance for engine detection.
            plugin_manager: PluginManager instance for plugin resolution.
        """
        self._detector = detector
        self._plugin_manager = plugin_manager

    def load(self, project_path: Path) -> ProjectLoadResult:
        """Load a project from the given path.

        This method orchestrates the entire project loading process:
        1. Validates the project path
        2. Detects the engine using ProjectDetector
        3. Resolves the appropriate plugin
        4. Gets structure specification from plugin
        5. Validates filesystem against specification
        6. Builds Project and related structures
        7. Returns ProjectLoadResult

        Args:
            project_path: Path to the project directory.

        Returns:
            ProjectLoadResult containing the loaded project (if successful),
            status, warnings, errors, and detection result.
        """
        try:
            return self._load_internal(project_path)
        except Exception as exc:
            LOGGER.exception(
                "Unexpected error during project loading for %s.",
                project_path,
            )
            # Return a safe result for unexpected errors
            error_issue = ProjectIssue(
                severity=ProjectIssueSeverity.ERROR,
                code="unexpected_error",
                message=f"Unexpected error during project loading: {exc}",
            )
            return ProjectLoadResult(
                status=ProjectLoadStatus.READ_ERROR,
                project=None,
                warnings=(),
                errors=(error_issue,),
                detection=None,
            )

    def _load_internal(self, project_path: Path) -> ProjectLoadResult:
        """Internal implementation of load() without top-level exception handling."""
        # Step 1: Validate initial path
        path_validation_result = self._validate_initial_path(project_path)
        if path_validation_result is not None:
            return path_validation_result

        # Step 2: Run detection
        detection = self._detector.detect(project_path)

        # Step 3: Handle detection status
        status_result = self._handle_detection_status(detection)
        if status_result is not None:
            return status_result

        # At this point, detection.status == DETECTED
        # Step 4: Resolve plugin
        plugin_id = detection.engine
        if plugin_id is None:
            # This should not happen if detection is DETECTED, but handle defensively
            issue = ProjectIssue(
                severity=ProjectIssueSeverity.ERROR,
                code="no_engine_detected",
                message="Detection returned DETECTED but no engine ID was provided.",
            )
            return ProjectLoadResult(
                status=ProjectLoadStatus.READ_ERROR,
                project=None,
                warnings=(),
                errors=(issue,),
                detection=detection,
            )

        plugin = self._plugin_manager.get(plugin_id)
        if plugin is None:
            issue = ProjectIssue(
                severity=ProjectIssueSeverity.ERROR,
                code="plugin_not_available",
                message=f"Plugin '{plugin_id}' is not available.",
            )
            return ProjectLoadResult(
                status=ProjectLoadStatus.READ_ERROR,
                project=None,
                warnings=(),
                errors=(issue,),
                detection=detection,
            )

        # Step 5: Get structure specification from plugin
        try:
            spec = plugin.describe_project_structure(project_path, detection)
        except Exception as exc:
            LOGGER.exception(
                "Plugin %s failed during describe_project_structure().",
                plugin_id,
            )
            issue = ProjectIssue(
                severity=ProjectIssueSeverity.ERROR,
                code="plugin_structure_error",
                message=f"Plugin {plugin_id} failed to describe structure: {exc}",
            )
            return ProjectLoadResult(
                status=ProjectLoadStatus.READ_ERROR,
                project=None,
                warnings=(),
                errors=(issue,),
                detection=detection,
            )

        # Step 6: Validate spec and build ProjectFile entries
        files, issues = self._validate_and_build_files(project_path, spec)

        # Separate warnings and errors
        warnings = tuple(i for i in issues if i.severity == ProjectIssueSeverity.WARNING)
        errors = tuple(i for i in issues if i.severity == ProjectIssueSeverity.ERROR)

        # Step 7: Determine project status based on errors
        has_blocking_errors = any(
            i.code in ("missing_expected_file", "missing_expected_directory")
            for i in errors
        )

        if has_blocking_errors:
            project_status = ProjectLoadStatus.INCOMPLETE
        else:
            project_status = ProjectLoadStatus.LOADED

        # Step 8: Build metadata
        metadata = ProjectMetadata(values=dict(spec.metadata))

        # Step 9: Build structure
        structure = ProjectStructure(
            root=project_path,
            entries=tuple(files),
            relevant_files=self._build_relevant_paths(project_path, spec.relevant_files),
            relevant_directories=self._build_relevant_paths(
                project_path, spec.relevant_directories
            ),
        )

        # Step 10: Build Project
        project = Project(
            path=project_path,
            engine=detection.engine,
            engine_display_name=detection.display_name,
            engine_version=detection.version,
            metadata=metadata,
            structure=structure,
            files=tuple(files),
            status=project_status,
            issues=tuple(issues),
            detection=detection,
        )

        # Step 11: Build ProjectLoadResult
        return ProjectLoadResult(
            status=project_status,
            project=project,
            warnings=warnings,
            errors=errors,
            detection=detection,
        )

    def _validate_initial_path(self, project_path: Path) -> ProjectLoadResult | None:
        """Validate the initial project path.

        Returns:
            ProjectLoadResult if validation fails, None if validation passes.
        """
        normalized_path = Path(project_path).resolve()

        if not normalized_path.exists():
            issue = ProjectIssue(
                severity=ProjectIssueSeverity.ERROR,
                code="invalid_path",
                message=f"Project path does not exist: {project_path}",
                path=normalized_path,
            )
            return ProjectLoadResult(
                status=ProjectLoadStatus.INVALID_PATH,
                project=None,
                warnings=(),
                errors=(issue,),
                detection=None,
            )

        if not normalized_path.is_dir():
            issue = ProjectIssue(
                severity=ProjectIssueSeverity.ERROR,
                code="invalid_path",
                message=f"Project path is not a directory: {project_path}",
                path=normalized_path,
            )
            return ProjectLoadResult(
                status=ProjectLoadStatus.INVALID_PATH,
                project=None,
                warnings=(),
                errors=(issue,),
                detection=None,
            )

        return None

    def _handle_detection_status(
        self,
        detection: DetectionResult,
    ) -> ProjectLoadResult | None:
        """Handle different detection statuses.

        Returns:
            ProjectLoadResult if status requires early return, None to continue.
        """
        if detection.status == DetectionStatus.UNKNOWN:
            issue = ProjectIssue(
                severity=ProjectIssueSeverity.ERROR,
                code="unknown_engine",
                message="No supported engine was detected for this project.",
                path=detection.project_path,
            )
            return ProjectLoadResult(
                status=ProjectLoadStatus.UNKNOWN_ENGINE,
                project=None,
                warnings=(),
                errors=(issue,),
                detection=detection,
            )

        if detection.status == DetectionStatus.CONFLICT:
            issue = ProjectIssue(
                severity=ProjectIssueSeverity.ERROR,
                code="engine_conflict",
                message="Multiple engine detectors matched this project.",
                path=detection.project_path,
            )
            return ProjectLoadResult(
                status=ProjectLoadStatus.ENGINE_CONFLICT,
                project=None,
                warnings=(),
                errors=(issue,),
                detection=detection,
            )

        if detection.status == DetectionStatus.INVALID_PATH:
            # Preserve the detection result but map to ProjectLoadStatus
            issue = ProjectIssue(
                severity=ProjectIssueSeverity.ERROR,
                code="invalid_path",
                message=detection.reason or "Invalid project path.",
                path=detection.project_path,
            )
            return ProjectLoadResult(
                status=ProjectLoadStatus.INVALID_PATH,
                project=None,
                warnings=(),
                errors=(issue,),
                detection=detection,
            )

        if detection.status == DetectionStatus.INCOMPLETE:
            # For INCOMPLETE, we may or may not have an engine
            if detection.engine is None:
                # Cannot build a partial project without knowing the engine
                return ProjectLoadResult(
                    status=ProjectLoadStatus.INCOMPLETE,
                    project=None,
                    warnings=(),
                    errors=(),
                    detection=detection,
                )

            # If we have an engine, we could potentially build a partial project,
            # but for safety we return INCOMPLETE without a project
            # This can be enhanced in future iterations if needed
            return ProjectLoadResult(
                status=ProjectLoadStatus.INCOMPLETE,
                project=None,
                warnings=(),
                errors=(),
                detection=detection,
            )

        # DETECTED - continue with loading
        return None

    def _validate_and_build_files(
        self,
        project_path: Path,
        spec: ProjectStructureSpec,
    ) -> tuple[tuple[ProjectFile, ...], tuple[ProjectIssue, ...]]:
        """Validate ProjectFileSpec entries and build ProjectFile instances.

        This method performs generic filesystem validation without interpreting
        file contents or executing anything.

        Args:
            project_path: Root path of the project.
            spec: ProjectStructureSpec from the plugin.

        Returns:
            Tuple of (ProjectFile entries, ProjectIssue instances).
        """
        files: list[ProjectFile] = []
        issues: list[ProjectIssue] = []
        seen_paths: set[Path] = set()

        # Process all specs from the specification
        all_specs: list[tuple[ProjectFileSpec, bool]] = []

        # Add expected files (required=True comes from spec)
        for file_spec in spec.expected_files:
            all_specs.append((file_spec, True))

        # Add expected directories
        for dir_spec in spec.expected_directories:
            all_specs.append((dir_spec, True))

        # Add relevant files (required=False)
        for file_spec in spec.relevant_files:
            all_specs.append((file_spec, False))

        # Add relevant directories
        for dir_spec in spec.relevant_directories:
            all_specs.append((dir_spec, False))

        for spec_entry, is_from_expected in all_specs:
            relative_path = spec_entry.relative_path

            # Check for path traversal attacks
            if not self._is_safe_relative_path(relative_path):
                issue = ProjectIssue(
                    severity=ProjectIssueSeverity.ERROR,
                    code="invalid_relative_path",
                    message=f"Unsafe path detected: {relative_path}",
                )
                issues.append(issue)
                continue

            # Consolidate duplicates - skip if already processed
            if relative_path in seen_paths:
                continue
            seen_paths.add(relative_path)

            full_path = project_path / relative_path

            # Check for symlinks
            is_symlink = full_path.is_symlink() if full_path.exists() else False

            if is_symlink:
                # Check if symlink points outside project root
                try:
                    resolved = full_path.resolve(strict=False)
                    project_root_resolved = project_path.resolve()
                    if not self._is_within_project(resolved, project_root_resolved):
                        # Symlink points outside project
                        if spec_entry.required:
                            issue = ProjectIssue(
                                severity=ProjectIssueSeverity.ERROR,
                                code="symlink_outside_project",
                                message=f"Required symlink points outside project: {relative_path}",
                                path=full_path,
                            )
                            issues.append(issue)
                            # Create ProjectFile with is_present=False
                            files.append(
                                ProjectFile(
                                    path=full_path,
                                    relative_path=relative_path,
                                    kind=ProjectFileKind.SYMLINK,
                                    role=spec_entry.role,
                                    size=None,
                                    modified_at=None,
                                    is_required=spec_entry.required,
                                    is_present=False,
                                )
                            )
                        else:
                            issue = ProjectIssue(
                                severity=ProjectIssueSeverity.WARNING,
                                code="symlink_skipped",
                                message=f"Optional symlink points outside project, skipped: {relative_path}",
                                path=full_path,
                            )
                            issues.append(issue)
                        continue
                except OSError as exc:
                    LOGGER.warning("Failed to resolve symlink %s: %s", full_path, exc)
                    issue = ProjectIssue(
                        severity=ProjectIssueSeverity.WARNING,
                        code="symlink_resolution_error",
                        message=f"Could not resolve symlink: {relative_path}",
                        path=full_path,
                    )
                    issues.append(issue)

            # Determine kind
            if is_symlink:
                kind = ProjectFileKind.SYMLINK
            elif full_path.is_file():
                kind = ProjectFileKind.FILE
            elif full_path.is_dir():
                kind = ProjectFileKind.DIRECTORY
            elif full_path.exists():
                kind = ProjectFileKind.OTHER
            else:
                kind = spec_entry.kind  # Use declared kind for missing items

            # Check existence
            is_present = full_path.exists() or full_path.is_symlink()

            # Get metadata if present
            size: int | None = None
            modified_at: float | None = None
            if is_present and not is_symlink:
                try:
                    stat_info = full_path.stat()
                    size = stat_info.st_size
                    modified_at = stat_info.st_mtime
                except OSError:
                    pass  # Leave as None

            # Create ProjectFile
            project_file = ProjectFile(
                path=full_path,
                relative_path=relative_path,
                kind=kind,
                role=spec_entry.role,
                size=size,
                modified_at=modified_at,
                is_required=spec_entry.required,
                is_present=is_present,
            )
            files.append(project_file)

            # Generate issues for missing required/optional items
            if not is_present:
                if spec_entry.kind == ProjectFileKind.DIRECTORY or kind == ProjectFileKind.DIRECTORY:
                    code = "missing_expected_directory"
                    item_type = "Directory"
                else:
                    code = "missing_expected_file"
                    item_type = "File"

                if spec_entry.required:
                    severity = ProjectIssueSeverity.ERROR
                else:
                    severity = ProjectIssueSeverity.WARNING

                issue = ProjectIssue(
                    severity=severity,
                    code=code,
                    message=f"{item_type} '{relative_path}' is {'required but' if spec_entry.required else 'optional and'} missing.",
                    path=full_path,
                )
                issues.append(issue)

        return tuple(files), tuple(issues)

    def _is_safe_relative_path(self, relative_path: Path) -> bool:
        """Check if a relative path is safe (no path traversal).

        Args:
            relative_path: Path to validate.

        Returns:
            True if the path is safe, False otherwise.
        """
        # Reject absolute paths
        if relative_path.is_absolute():
            return False

        # Normalize and check for path traversal
        try:
            # Convert to string and check for suspicious patterns
            path_str = str(relative_path)
            if ".." in path_str.split("/") or ".." in path_str.split("\\"):
                # More thorough check - resolve and see if it escapes
                # We can't resolve without a base, so check components
                parts = relative_path.parts
                for part in parts:
                    if part == "..":
                        return False
            return True
        except (ValueError, TypeError):
            return False

    def _is_within_project(self, path: Path, project_root: Path) -> bool:
        """Check if a resolved path is within the project root.

        Args:
            path: Resolved path to check.
            project_root: Resolved project root path.

        Returns:
            True if path is within project_root, False otherwise.
        """
        try:
            path.relative_to(project_root)
            return True
        except ValueError:
            return False

    def _build_relevant_paths(
        self,
        project_path: Path,
        specs: tuple[ProjectFileSpec, ...],
    ) -> tuple[Path, ...]:
        """Build tuple of relevant paths from specs.

        Args:
            project_path: Root path of the project.
            specs: ProjectFileSpec instances.

        Returns:
            Tuple of full paths.
        """
        paths: list[Path] = []
        seen: set[Path] = set()

        for spec_entry in specs:
            relative_path = spec_entry.relative_path
            if relative_path in seen:
                continue
            seen.add(relative_path)

            if not self._is_safe_relative_path(relative_path):
                continue

            full_path = project_path / relative_path
            paths.append(full_path)

        return tuple(paths)
