"""Entry point for RPG Translator Suite."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.core.application import Application
from app.gui.main_window import MainWindow

LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Start the RTS desktop application."""
    base_path = Path(__file__).resolve().parent
    core_application = Application(base_path=base_path)
    core_application.initialize()

    qt_application = QApplication(sys.argv)
    main_window = MainWindow(application=core_application)
    main_window.show()

    LOGGER.info("RTS GUI started")
    return qt_application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
