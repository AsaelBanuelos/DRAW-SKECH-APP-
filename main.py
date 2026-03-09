"""
RealSketch — Main entry point.
Desktop application to convert photos into realistic drawing guides.
"""

import sys
import os

# Ensure root directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.main_window import MainWindow


def main():
    """Initialize and run the application."""
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("RealSketch")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("RealSketch")

    # Global readable font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Global app style
    app.setStyleSheet(_get_stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def _get_stylesheet() -> str:
    """Returns the global application stylesheet."""
    return """
    QMainWindow {
        background-color: #1e1e2e;
    }

    QWidget {
        color: #cdd6f4;
        background-color: #1e1e2e;
    }

    QPushButton {
        background-color: #45475a;
        color: #cdd6f4;
        border: 1px solid #585b70;
        border-radius: 6px;
        padding: 8px 18px;
        font-size: 13px;
        font-weight: 500;
    }

    QPushButton:hover {
        background-color: #585b70;
        border-color: #89b4fa;
    }

    QPushButton:pressed {
        background-color: #313244;
    }

    QPushButton:disabled {
        background-color: #313244;
        color: #6c7086;
        border-color: #45475a;
    }

    QPushButton#btnPrimary {
        background-color: #89b4fa;
        color: #1e1e2e;
        font-weight: 600;
    }

    QPushButton#btnPrimary:hover {
        background-color: #b4d0fb;
    }

    QPushButton#btnPrimary:disabled {
        background-color: #45475a;
        color: #6c7086;
    }

    QPushButton#btnExport {
        background-color: #a6e3a1;
        color: #1e1e2e;
        font-weight: 600;
    }

    QPushButton#btnExport:hover {
        background-color: #c6f0c1;
    }

    QPushButton#btnExport:disabled {
        background-color: #45475a;
        color: #6c7086;
    }

    QTabWidget::pane {
        border: 1px solid #45475a;
        border-radius: 4px;
        background-color: #181825;
    }

    QTabBar::tab {
        background-color: #313244;
        color: #a6adc8;
        border: 1px solid #45475a;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }

    QTabBar::tab:selected {
        background-color: #45475a;
        color: #cdd6f4;
        border-bottom-color: #45475a;
    }

    QTabBar::tab:hover {
        background-color: #585b70;
    }

    QLabel#statusLabel {
        color: #a6adc8;
        font-size: 12px;
        padding: 4px 8px;
    }

    QLabel#titleLabel {
        color: #cdd6f4;
        font-size: 16px;
        font-weight: 700;
    }

    QScrollArea {
        border: none;
        background-color: #181825;
    }

    QTextEdit {
        background-color: #181825;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 4px;
        padding: 8px;
        font-size: 13px;
    }

    QProgressBar {
        border: 1px solid #45475a;
        border-radius: 4px;
        text-align: center;
        background-color: #313244;
        color: #cdd6f4;
    }

    QProgressBar::chunk {
        background-color: #89b4fa;
        border-radius: 3px;
    }

    QSplitter::handle {
        background-color: #45475a;
        width: 2px;
    }
    """


if __name__ == "__main__":
    main()
