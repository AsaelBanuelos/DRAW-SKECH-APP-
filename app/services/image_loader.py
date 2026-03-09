"""
RealSketch — Image loading service.

Handles loading image files from disk,
format validation and conversion to numpy array for OpenCV.
"""

import os
import cv2
import numpy as np
from typing import Optional, Tuple

# Supported image formats
SUPPORTED_FORMATS = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif")
SUPPORTED_FILTER = "Images (*.jpg *.jpeg *.png *.bmp *.webp *.tiff *.tif);;All files (*.*)"


def load_image(file_path: str) -> Optional[np.ndarray]:
    """
    Load an image from disk.

    Args:
        file_path: Absolute path to the image file.

    Returns:
        Image as BGR numpy array, or None if loading fails.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the format is not supported.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format: {ext}. "
            f"Valid formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    # Read image with OpenCV (supports paths with special characters)
    image = cv2.imdecode(
        np.fromfile(file_path, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(f"Could not decode image: {file_path}")

    return image


def get_image_info(image: np.ndarray) -> dict:
    """
    Return basic image information.

    Args:
        image: Image as numpy array.

    Returns:
        Dictionary with width, height, channels, dtype.
    """
    h, w = image.shape[:2]
    channels = image.shape[2] if len(image.shape) == 3 else 1

    return {
        "width": w,
        "height": h,
        "channels": channels,
        "dtype": str(image.dtype),
        "size_mb": round(image.nbytes / (1024 * 1024), 2),
    }
