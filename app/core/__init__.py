"""Core package for engine-independent RTS services."""

from app.core.application import Application
from app.core.config_manager import ConfigManager
from app.core.detection import (
    ConfidenceLevel,
    DetectionEvidence,
    DetectionResult,
    DetectionStatus,
)
from app.core.exceptions import PluginError, PluginRegistrationError, RTSException
from app.core.logger import configure_logging
from app.core.plugin_loader import PluginLoader
from app.core.project_detector import ProjectDetector
from app.core.plugin_manager import PluginManager
from app.core.plugin_registry import PluginRegistry
from app.core.plugin_state import PluginState
from app.core.version import __version__

__all__ = [
    "Application",
    "ConfigManager",
    "ConfidenceLevel",
    "DetectionEvidence",
    "DetectionResult",
    "DetectionStatus",
    "PluginError",
    "PluginLoader",
    "ProjectDetector",
    "PluginManager",
    "PluginRegistrationError",
    "PluginRegistry",
    "PluginState",
    "RTSException",
    "__version__",
    "configure_logging",
]
