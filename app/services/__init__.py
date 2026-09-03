"""Services layer for RPG Translator Suite.

This module contains concrete service implementations that extend the core
functionality, such as translation providers, external API integrations, etc.
"""

from app.services.encoding_handler import (
    EncodingDetector,
    EncodingHandler,
    EncodingInfo,
    EncodingType,
    FileReadResult,
    detect_encoding,
    read_text_file,
    write_text_file,
)
from app.services.validator import (
    ProjectValidator,
    ValidationIssue,
    ValidationIssueType,
    ValidationResult,
    ValidationSeverity,
)

__all__ = [
    # Encoding
    "EncodingDetector",
    "EncodingHandler",
    "EncodingInfo",
    "EncodingType",
    "FileReadResult",
    "detect_encoding",
    "read_text_file",
    "write_text_file",
    # Validator
    "ProjectValidator",
    "ValidationIssue",
    "ValidationIssueType",
    "ValidationResult",
    "ValidationSeverity",
]
