"""Tests for the project engine detection pipeline."""

from pathlib import Path

from app.core.base_plugin import BasePlugin
from app.core.detection import ConfidenceLevel, DetectionResult, DetectionStatus
from app.core.plugin_loader import PluginLoader
from app.core.plugin_registry import PluginRegistry
from app.core.project_detector import ProjectDetector
from plugins.rpgmaker_mv import RPGMakerMVPlugin


class AlwaysDetectPlugin(BasePlugin):
    """Test detector that always reports a detected engine."""

    plugin_id = "test_engine"
    display_name = "Test Engine"

    def detect(self, project_path: Path) -> bool:
        return True

    def detect_project(self, project_path: Path) -> DetectionResult:
        return DetectionResult(
            status=DetectionStatus.DETECTED,
            project_path=project_path,
            engine=self.plugin_id,
            display_name=self.display_name,
            confidence=ConfidenceLevel.HIGH,
        )


class UnknownPlugin(BasePlugin):
    """Test detector that never recognizes a project."""

    plugin_id = "unknown_test_engine"
    display_name = "Unknown Test Engine"

    def detect(self, project_path: Path) -> bool:
        return False


def _detector_with(*plugins: BasePlugin) -> ProjectDetector:
    registry = PluginRegistry()
    for plugin in plugins:
        registry.register(plugin)
    return ProjectDetector(PluginLoader(Path("plugins"), registry))


def _create_mv_project(project_path: Path, version: str | None = "1.6.1") -> None:
    (project_path / "www" / "data").mkdir(parents=True)
    (project_path / "www" / "js").mkdir(parents=True)
    (project_path / "package.json").write_text(
        '{"main":"index.html","scripts":["www/js/rpg_core.js"]}',
        encoding="utf-8",
    )
    (project_path / "www" / "data" / "System.json").write_text(
        "{}",
        encoding="utf-8",
    )
    rpg_core_text = "// RPG Maker MV v1.6.1" if version else "// RPG Maker MV"
    (project_path / "www" / "js" / "rpg_core.js").write_text(
        rpg_core_text,
        encoding="utf-8",
    )


def test_detects_valid_rpg_maker_mv_project(tmp_path) -> None:
    """A valid MV project returns a structured high-confidence result."""
    _create_mv_project(tmp_path)
    result = _detector_with(RPGMakerMVPlugin()).detect(tmp_path)

    assert result.status == DetectionStatus.DETECTED
    assert result.engine == "rpgmaker_mv"
    assert result.display_name == "RPG Maker MV"
    assert result.version == "1.6.1"
    assert result.confidence == ConfidenceLevel.HIGH
    assert len(result.evidence) == 3


def test_detects_mv_without_version_information(tmp_path) -> None:
    """MV may be detected even when runtime version text is absent."""
    _create_mv_project(tmp_path, version=None)
    result = _detector_with(RPGMakerMVPlugin()).detect(tmp_path)

    assert result.status == DetectionStatus.DETECTED
    assert result.engine == "rpgmaker_mv"
    assert result.version is None
    assert result.confidence == ConfidenceLevel.MEDIUM
    assert result.reason == "Engine detected, but version could not be determined."


def test_folder_that_is_not_a_project_returns_unknown(tmp_path) -> None:
    """An arbitrary folder is represented as an unknown engine."""
    result = _detector_with(RPGMakerMVPlugin()).detect(tmp_path)

    assert result.status == DetectionStatus.UNKNOWN
    assert result.reason == "No supported engine detected."


def test_incomplete_project_is_not_silently_detected(tmp_path) -> None:
    """Partial MV evidence is reported as incomplete by the plugin."""
    (tmp_path / "www" / "data").mkdir(parents=True)
    (tmp_path / "www" / "data" / "System.json").write_text(
        "{}",
        encoding="utf-8",
    )

    result = RPGMakerMVPlugin().detect_project(tmp_path)

    assert result.status == DetectionStatus.INCOMPLETE
    assert result.confidence == ConfidenceLevel.LOW
    assert result.reason == "RPG Maker MV evidence was found, but the project appears incomplete."


def test_multiple_detection_results_return_conflict(tmp_path) -> None:
    """The Core exposes multiple positive detector matches as a conflict."""
    _create_mv_project(tmp_path)
    result = _detector_with(RPGMakerMVPlugin(), AlwaysDetectPlugin()).detect(tmp_path)

    assert result.status == DetectionStatus.CONFLICT
    assert result.reason == "Multiple engine detectors matched this project."
    assert {conflict.engine for conflict in result.conflicts} == {"rpgmaker_mv", "test_engine"}


def test_unknown_engine_when_no_plugin_matches(tmp_path) -> None:
    """Registered plugins that do not match produce an unknown result."""
    result = _detector_with(UnknownPlugin()).detect(tmp_path)

    assert result.status == DetectionStatus.UNKNOWN
    assert result.reason == "No supported engine detected."


def test_invalid_path_returns_invalid_path_result(tmp_path) -> None:
    """Missing paths are represented explicitly instead of raising."""
    missing_path = tmp_path / "missing"
    result = _detector_with(RPGMakerMVPlugin()).detect(missing_path)

    assert result.status == DetectionStatus.INVALID_PATH
    assert result.reason == "Project path does not exist or is not a directory."
