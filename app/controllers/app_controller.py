"""
RealSketch — Main application controller.

Orchestrates the processing pipeline:
load → preprocessing → detection → guide generation → results.

Connects the UI with services and processing modules.
"""

import os
import traceback
import numpy as np
from typing import Optional

from PySide6.QtCore import QObject, Signal, QThread

from app.models.result_models import ProcessingResult
from app.services.image_loader import load_image, get_image_info
from app.services.export_service import (
    export_all,
    export_single,
    get_default_export_dir,
    generate_export_folder_name,
)
from app.core.preprocess import preprocess_image
from app.core.face_landmarks import FaceLandmarkDetector
from app.core.sketch_generator import generate_sketch
from app.core.tone_mapper import generate_tone_map
from app.core.shading_guide import generate_shading_guide


class ProcessingWorker(QThread):
    """
    Worker thread to execute the processing pipeline
    without blocking the graphical interface.
    """

    # Signals
    progress = Signal(str, int)      # (message, percentage 0-100)
    finished = Signal(ProcessingResult)
    error = Signal(str)

    def __init__(self, image: np.ndarray, parent=None):
        super().__init__(parent)
        self.image = image

    def run(self):
        """Execute the complete processing pipeline."""
        result = ProcessingResult()

        try:
            # Step 1: Preprocess
            self.progress.emit("Preprocessing image...", 10)
            result.original = self.image.copy()
            result.preprocessed = preprocess_image(self.image)

            # Step 2: Detect face
            self.progress.emit("Detecting face...", 25)
            detector = FaceLandmarkDetector()
            try:
                result.face_landmarks = detector.detect(result.preprocessed)
                result.has_face = result.face_landmarks.detected
            finally:
                detector.close()

            face = result.face_landmarks

            # Step 3: Sketch (pencil-style contours)
            self.progress.emit("Generating sketch...", 40)
            result.sketch = generate_sketch(result.preprocessed)

            # Step 4: Shading
            self.progress.emit("Generating shading guide...", 60)
            result.shading = generate_shading_guide(result.preprocessed, face)

            # Step 5: Values (tone map)
            self.progress.emit("Generating tone map...", 80)
            result.tone_map = generate_tone_map(result.preprocessed, levels=5)

            self.progress.emit("Processing complete!", 100)
            self.finished.emit(result)

        except Exception as e:
            error_msg = f"Processing error: {str(e)}\n{traceback.format_exc()}"
            result.error = error_msg
            self.error.emit(str(e))


class AppController(QObject):
    """
    Main application controller.

    Manages state, coordinates between UI and processing,
    and handles image loading/exporting.
    """

    # Signals for the UI
    image_loaded = Signal(np.ndarray)            # Loaded original image
    processing_started = Signal()
    processing_progress = Signal(str, int)       # (message, percentage)
    processing_finished = Signal(ProcessingResult)
    processing_error = Signal(str)
    export_finished = Signal(str)                # Result message
    status_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_image: Optional[np.ndarray] = None
        self._current_result: Optional[ProcessingResult] = None
        self._worker: Optional[ProcessingWorker] = None
        self._image_path: Optional[str] = None

    @property
    def has_image(self) -> bool:
        """Is there a loaded image?"""
        return self._current_image is not None

    @property
    def has_result(self) -> bool:
        """Are there processing results?"""
        return self._current_result is not None and self._current_result.is_valid

    @property
    def current_result(self) -> Optional[ProcessingResult]:
        """Current processing result."""
        return self._current_result

    def load_image(self, file_path: str):
        """
        Load an image from disk.

        Args:
            file_path: Path to the image file.
        """
        try:
            self.status_message.emit(f"Loading: {os.path.basename(file_path)}...")
            image = load_image(file_path)

            if image is not None:
                self._current_image = image
                self._image_path = file_path
                self._current_result = None  # Reset previous result

                info = get_image_info(image)
                self.status_message.emit(
                    f"Image loaded: {info['width']}×{info['height']} px | "
                    f"{info['size_mb']} MB"
                )
                self.image_loaded.emit(image)
            else:
                self.status_message.emit("Error: could not load the image.")

        except Exception as e:
            self.status_message.emit(f"Error: {str(e)}")
            self.processing_error.emit(str(e))

    def process_image(self):
        """
        Start the processing pipeline in a separate thread.
        """
        if not self.has_image:
            self.status_message.emit("Load an image first.")
            return

        # Avoid double processing
        if self._worker is not None and self._worker.isRunning():
            self.status_message.emit("Processing already in progress...")
            return

        self.processing_started.emit()

        # Create and execute worker
        self._worker = ProcessingWorker(self._current_image)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def export_results(self, output_dir: Optional[str] = None):
        """
        Export all results to a folder.

        Args:
            output_dir: Destination directory. If None, uses the default.
        """
        if not self.has_result:
            self.status_message.emit("No results to export. Process an image first.")
            return

        try:
            if output_dir is None:
                base = get_default_export_dir()
                folder_name = generate_export_folder_name()
                output_dir = os.path.join(base, folder_name)

            exported = export_all(self._current_result, output_dir)

            if exported:
                msg = f"Exported {len(exported)} files to: {output_dir}"
                self.status_message.emit(msg)
                self.export_finished.emit(output_dir)
            else:
                self.status_message.emit("Could not export any files.")

        except Exception as e:
            self.status_message.emit(f"Export error: {str(e)}")

    def export_single_result(self, name: str, image: np.ndarray, file_path: str):
        """Export an individual result."""
        try:
            saved_path = export_single(image, file_path)
            self.status_message.emit(f"Exported: {os.path.basename(saved_path)}")
        except Exception as e:
            self.status_message.emit(f"Export error: {str(e)}")

    # --- Internal callbacks ---

    def _on_progress(self, message: str, percent: int):
        """Worker progress callback."""
        self.processing_progress.emit(message, percent)
        self.status_message.emit(message)

    def _on_finished(self, result: ProcessingResult):
        """Callback when processing finishes."""
        self._current_result = result

        if result.has_face:
            self.status_message.emit(
                "✓ Processing complete — Face detected, portrait guides generated."
            )
        else:
            self.status_message.emit(
                "✓ Processing complete — Generic mode (no face detected)."
            )

        self.processing_finished.emit(result)

    def _on_error(self, error_msg: str):
        """Worker error callback."""
        self.status_message.emit(f"Error: {error_msg}")
        self.processing_error.emit(error_msg)
