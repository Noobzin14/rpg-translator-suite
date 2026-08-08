"""Logging setup for RPG Translator Suite."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.constants import LOG_FILE_NAME

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(log_directory: Path, level: int = logging.INFO) -> None:
    """Configure application logging.

    Args:
        log_directory: Directory where application log files are stored.
        level: Logging level used by the root logger.
    """
    log_directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=level,
        format=DEFAULT_LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_directory / LOG_FILE_NAME, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
