"""Main window for RPG Translator Suite."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

from app.core.application import Application


class MainWindow(QMainWindow):
    """Initial RTS main window with the Sprint 0.1 home screen."""

    def __init__(self, application: Application) -> None:
        """Create the main window.

        Args:
            application: Initialized core application object.
        """
        super().__init__()
        self._application = application
        self.setWindowTitle("RPG Translator Suite")
        self.resize(900, 600)
        self.setCentralWidget(self._build_home_widget())

    def _build_home_widget(self) -> QWidget:
        """Build the initial home screen widget."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("RPG Translator Suite", container)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        open_project_button = QPushButton("Open Project", container)
        open_project_button.setObjectName("openProjectButton")

        layout.addWidget(title)
        layout.addWidget(open_project_button)
        return container
