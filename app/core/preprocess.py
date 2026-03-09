"""RealSketch — Image preprocessing.

Loads, resizes and normalizes the image for the pipeline.
Correctly handles: color, grayscale, BGRA, RGBA,
images with alpha channel, low contrast, etc.
"""

import cv2
import numpy as np
from typing import Tuple

# Maximum processing size (longest side)
MAX_PROCESSING_SIZE = 1400


def preprocess_image(
    image: np.ndarray,
    max_size: int = MAX_PROCESSING_SIZE,
) -> np.ndarray:
    """
    Preprocess the image for the analysis pipeline.

    1. Ensures BGR 3-channel format.
    2. Normalizes contrast if the image is very flat.
    3. Resizes if it exceeds max_size.

    Args:
        image: Numpy array image (BGR, BGRA, gray, etc.).
        max_size: Maximum size of the longest side in pixels.

    Returns:
        Preprocessed image as BGR uint8 numpy array.
    """
    if image is None:
        raise ValueError("The provided image is None.")

    processed = ensure_bgr(image.copy())

    # -- Normalize contrast if dynamic range is very low --
    gray_check = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
    lo, hi = int(np.percentile(gray_check, 1)), int(np.percentile(gray_check, 99))
    if (hi - lo) < 80:  # very flat / low contrast image
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        processed = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # -- Resize if too large --
    h, w = processed.shape[:2]
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        processed = cv2.resize(
            processed, (new_w, new_h), interpolation=cv2.INTER_AREA
        )

    return processed


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert BGR image to grayscale."""
    if len(image.shape) == 2:
        return image.copy()
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def enhance_contrast(gray: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    """Enhance contrast using CLAHE."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    return clahe.apply(gray)


def get_image_dimensions(image: np.ndarray) -> Tuple[int, int]:
    """Return (width, height) of the image."""
    h, w = image.shape[:2]
    return w, h


def ensure_bgr(image: np.ndarray) -> np.ndarray:
    """Ensure the image is in BGR 3-channel format."""
    if image is None:
        raise ValueError("Image is None.")
    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    channels = image.shape[2]
    if channels == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    if channels == 1:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return image
