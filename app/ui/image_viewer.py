"""
RealSketch — Image viewer.

Reusable widget to display images (numpy arrays) in the Qt UI.
Supports proportional scaling, scroll and container size adaptation.
"""

import cv2
import numpy as np
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QScrollArea, QSizePolicy
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, Signal


class ImageViewer(QWidget):
    """
    Widget to display an image with automatic scaling.

    Converts a numpy array (OpenCV BGR) to QPixmap and displays
    it centered in the widget, respecting aspect ratio.
    """

    clicked = Signal()

    def __init__(self, placeholder_text: str = "No image", parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._numpy_image = None
        self._placeholder_text = placeholder_text

        self._setup_ui()

    def _setup_ui(self):
        """Configure the viewer interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel(self._placeholder_text)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._label.setMinimumSize(200, 200)
        self._label.setStyleSheet("""
            QLabel {
                background-color: #181825;
                color: #6c7086;
                font-size: 14px;
                border: 1px dashed #45475a;
                border-radius: 8px;
            }
        """)

        layout.addWidget(self._label)

    def set_image(self, image: np.ndarray):
        """
        Display an image (BGR numpy array) in the viewer.

        Args:
            image: BGR image as OpenCV numpy array.
        """
        if image is None:
            self.clear()
            return

        self._numpy_image = image.copy()

        # Convert BGR to RGB
        if len(image.shape) == 3:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            q_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            # Grayscale
            h, w = image.shape
            q_image = QImage(image.data, w, h, w, QImage.Format_Grayscale8)

        self._pixmap = QPixmap.fromImage(q_image)
        self._update_display()

    def clear(self):
        """Clear the viewer and show the placeholder."""
        self._pixmap = None
        self._numpy_image = None
        self._label.setPixmap(QPixmap())
        self._label.setText(self._placeholder_text)

    def get_numpy_image(self) -> np.ndarray:
        """Return the current image as a BGR numpy array."""
        return self._numpy_image

    def resizeEvent(self, event):
        """When resizing the widget, rescale the image."""
        super().resizeEvent(event)
        if self._pixmap:
            self._update_display()

    def _update_display(self):
        """Update the scaled pixmap to the current label size."""
        if self._pixmap is None:
            return

        # Scale keeping aspect ratio
        available = self._label.size()
        scaled = self._pixmap.scaled(
            available,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self._label.setText("")
        self._label.setPixmap(scaled)

    def mousePressEvent(self, event):
        """Emit click signal."""
        super().mousePressEvent(event)
        self.clicked.emit()
