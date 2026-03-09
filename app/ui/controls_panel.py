"""
RealSketch — Controls panel.

Contains the main buttons: Load, Process, Export
and the progress bar.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QProgressBar, QLabel, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt


class ControlsPanel(QWidget):
    """
    Panel with action buttons and progress bar.
    """

    # Signals that the main window will connect to the controller
    load_clicked = Signal()
    process_clicked = Signal()
    export_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Build the controls panel interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # App title
        title = QLabel("RealSketch")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Turn photos into drawing guides")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6c7086; font-size: 11px; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        # --- Load Button ---
        self.btn_load = QPushButton("📂  Load Image")
        self.btn_load.setMinimumHeight(42)
        self.btn_load.setCursor(Qt.PointingHandCursor)
        self.btn_load.clicked.connect(self.load_clicked.emit)
        layout.addWidget(self.btn_load)

        # --- Process Button ---
        self.btn_process = QPushButton("⚙  Process")
        self.btn_process.setObjectName("btnPrimary")
        self.btn_process.setMinimumHeight(42)
        self.btn_process.setEnabled(False)
        self.btn_process.setCursor(Qt.PointingHandCursor)
        self.btn_process.clicked.connect(self.process_clicked.emit)
        layout.addWidget(self.btn_process)

        # --- Progress bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # --- Progress label ---
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #89b4fa; font-size: 11px;")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # --- Visual separator ---
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #45475a;")
        layout.addWidget(separator)

        # --- Export Button ---
        self.btn_export = QPushButton("💾  Export All")
        self.btn_export.setObjectName("btnExport")
        self.btn_export.setMinimumHeight(42)
        self.btn_export.setEnabled(False)
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_clicked.emit)
        layout.addWidget(self.btn_export)

        # --- Loaded image info ---
        self.image_info_label = QLabel("No image loaded")
        self.image_info_label.setAlignment(Qt.AlignCenter)
        self.image_info_label.setWordWrap(True)
        self.image_info_label.setStyleSheet(
            "color: #6c7086; font-size: 11px; padding: 4px;"
        )
        layout.addWidget(self.image_info_label)

        # Push everything up
        layout.addStretch()

        # --- App info at the bottom ---
        version_label = QLabel("v1.0.0 — 100% local")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #45475a; font-size: 10px;")
        layout.addWidget(version_label)

    def set_image_loaded(self, info_text: str):
        """Update the UI when an image is loaded."""
        self.btn_process.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.image_info_label.setText(info_text)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(False)

    def set_processing_started(self):
        """Update the UI when processing starts."""
        self.btn_load.setEnabled(False)
        self.btn_process.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting...")

    def set_processing_progress(self, message: str, percent: int):
        """Update the progress bar."""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def set_processing_finished(self):
        """Update the UI when processing finishes."""
        self.btn_load.setEnabled(True)
        self.btn_process.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.progress_bar.setValue(100)
        self.progress_label.setText("Done!")

    def set_processing_error(self):
        """Update the UI when there is a processing error."""
        self.btn_load.setEnabled(True)
        self.btn_process.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Processing error")
        self.progress_label.setStyleSheet("color: #f38ba8; font-size: 11px;")
