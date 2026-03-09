"""
RealSketch — Main window.

Orchestrates all UI panels, connects the controller
and manages the application flow.
"""

import os
import numpy as np

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QTabWidget, QLabel, QFileDialog, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction

from app.ui.image_viewer import ImageViewer
from app.ui.controls_panel import ControlsPanel
from app.controllers.app_controller import AppController
from app.models.result_models import ProcessingResult
from app.services.image_loader import SUPPORTED_FILTER
from app.services.export_service import get_default_export_dir, generate_export_folder_name


class MainWindow(QMainWindow):
    """
    RealSketch main window.

    Layout:
    ┌──────────────┬──────────────────────────────────┐
    │  Controls    │     Left panel    │  Tabs     │
    │  (buttons)   │     (original)       │  right   │
    │              │                      │           │
    └──────────────┴──────────────────────────────────┘
    │                  Status bar                      │
    └──────────────────────────────────────────────────┘
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("RealSketch — Realistic Drawing Guide")
        self.setMinimumSize(1100, 700)
        self.resize(1400, 850)

        # Controller
        self._controller = AppController(self)

        # Build UI
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Build the entire window interface."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # ================================
        # Left panel: controls
        # ================================
        self._controls = ControlsPanel()
        self._controls.setFixedWidth(220)
        main_layout.addWidget(self._controls)

        # ================================
        # Central splitter: original + tabs
        # ================================
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(3)

        # --- Original image viewer ---
        original_container = QWidget()
        original_layout = QVBoxLayout(original_container)
        original_layout.setContentsMargins(0, 0, 0, 0)
        original_layout.setSpacing(4)

        original_header = QLabel("📷  Original Image")
        original_header.setStyleSheet(
            "color: #a6adc8; font-size: 12px; font-weight: 600; padding: 4px 8px;"
        )
        original_layout.addWidget(original_header)

        self._original_viewer = ImageViewer("Load an image to get started")
        original_layout.addWidget(self._original_viewer)

        splitter.addWidget(original_container)

        # --- Results panel with tabs ---
        results_container = QWidget()
        results_layout = QVBoxLayout(results_container)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(4)

        results_header = QLabel("🎨  Results")
        results_header.setStyleSheet(
            "color: #a6adc8; font-size: 12px; font-weight: 600; padding: 4px 8px;"
        )
        results_layout.addWidget(results_header)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        # Tab 1: Sketch
        self._sketch_viewer = ImageViewer("Sketch will appear here")
        self._tabs.addTab(self._sketch_viewer, "Sketch")

        # Tab 2: Shading
        self._shading_viewer = ImageViewer("Shading guide will appear here")
        self._tabs.addTab(self._shading_viewer, "Shading")

        # Tab 3: Values (tone map)
        self._values_viewer = ImageViewer("Tone map will appear here")
        self._tabs.addTab(self._values_viewer, "Values")

        results_layout.addWidget(self._tabs)

        splitter.addWidget(results_container)

        # Splitter ratio: 45% original, 55% results
        splitter.setSizes([450, 550])

        main_layout.addWidget(splitter, stretch=1)

        # ================================
        # Status bar
        # ================================
        self._status_label = QLabel("Welcome to RealSketch — Load an image to get started")
        self._status_label.setObjectName("statusLabel")
        self.statusBar().addPermanentWidget(self._status_label, 1)

    def _connect_signals(self):
        """Connect all signals between UI and controller."""
        # Controls → Actions
        self._controls.load_clicked.connect(self._on_load_clicked)
        self._controls.process_clicked.connect(self._on_process_clicked)
        self._controls.export_clicked.connect(self._on_export_clicked)

        # Controller → UI
        self._controller.image_loaded.connect(self._on_image_loaded)
        self._controller.processing_started.connect(self._on_processing_started)
        self._controller.processing_progress.connect(self._on_processing_progress)
        self._controller.processing_finished.connect(self._on_processing_finished)
        self._controller.processing_error.connect(self._on_processing_error)
        self._controller.status_message.connect(self._on_status_message)
        self._controller.export_finished.connect(self._on_export_finished)

    # =========================================================================
    # Button handlers
    # =========================================================================

    def _on_load_clicked(self):
        """Open dialog to select an image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select image",
            "",
            SUPPORTED_FILTER,
        )
        if file_path:
            self._controller.load_image(file_path)

    def _on_process_clicked(self):
        """Start processing."""
        self._controller.process_image()

    def _on_export_clicked(self):
        """Open dialog to select export folder."""
        base_dir = get_default_export_dir()
        folder_name = generate_export_folder_name()
        default_path = os.path.join(base_dir, folder_name)

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select export folder",
            base_dir,
        )

        if output_dir:
            # Create subfolder with timestamp
            final_dir = os.path.join(output_dir, folder_name)
            self._controller.export_results(final_dir)

    # =========================================================================
    # Controller handlers
    # =========================================================================

    def _on_image_loaded(self, image: np.ndarray):
        """Executed when an image is successfully loaded."""
        self._original_viewer.set_image(image)

        h, w = image.shape[:2]
        self._controls.set_image_loaded(f"{w} × {h} px")

        # Clear previous results
        self._sketch_viewer.clear()
        self._shading_viewer.clear()
        self._values_viewer.clear()

    def _on_processing_started(self):
        """Executed when processing starts."""
        self._controls.set_processing_started()

    def _on_processing_progress(self, message: str, percent: int):
        """Update progress."""
        self._controls.set_processing_progress(message, percent)

    def _on_processing_finished(self, result: ProcessingResult):
        """Executed when processing finishes."""
        self._controls.set_processing_finished()

        # Show results in each tab
        if result.sketch and result.sketch.image is not None:
            self._sketch_viewer.set_image(result.sketch.image)

        if result.shading and result.shading.image is not None:
            self._shading_viewer.set_image(result.shading.image)

        if result.tone_map and result.tone_map.image is not None:
            self._values_viewer.set_image(result.tone_map.image)

        # Switch to first tab automatically
        self._tabs.setCurrentIndex(0)

        # Show status
        if result.has_face:
            self._on_status_message(
                "✓ Face detected — Portrait guides generated on all tabs."
            )
        else:
            self._on_status_message(
                "✓ Processing complete — Generic mode (no face). "
                "Check each tab."
            )

    def _on_processing_error(self, error_msg: str):
        """Executed when there is a processing error."""
        self._controls.set_processing_error()

        QMessageBox.warning(
            self,
            "Processing Error",
            f"An error occurred during analysis:\n\n{error_msg}\n\n"
            "Try with another image.",
        )

    def _on_status_message(self, message: str):
        """Update the status bar message."""
        self._status_label.setText(message)

    def _on_export_finished(self, output_dir: str):
        """Executed when export finishes."""
        QMessageBox.information(
            self,
            "Export Complete",
            f"Results saved to:\n\n{output_dir}",
        )
