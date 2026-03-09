"""RealSketch — Sketch generator (drawing lines).

Converts the photograph into a clean contour drawing
with a pencil-on-paper style: thin dark lines on a light background.

Auto-adapts to the resolution and contrast of the image
to produce optimal results with any type of photo
(color, B&W, low contrast, high resolution, etc.).
"""

import cv2
import numpy as np

from app.models.result_models import SketchResult


def generate_sketch(image: np.ndarray, **_kw) -> SketchResult:
    """Generate a pencil-style contour sketch.

    Auto-adapts parameters based on resolution and contrast.
    """
    result = SketchResult()
    h, w = image.shape[:2]
    short_side = min(h, w)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # --- 0. Normalize contrast if needed ---
    lo, hi = int(np.percentile(gray, 2)), int(np.percentile(gray, 98))
    if (hi - lo) < 100:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

    # --- 1. Reduce noise while preserving edges ---
    #     Adapt median to image size
    med_k = 5 if short_side < 600 else 7
    gray = cv2.medianBlur(gray, med_k)

    #     Bilateral: sigma proportional to size
    sigma = max(50, min(200, short_side // 4))
    gray = cv2.bilateralFilter(gray, d=9, sigmaColor=sigma, sigmaSpace=sigma)
    gray = cv2.bilateralFilter(gray, d=7, sigmaColor=sigma, sigmaSpace=sigma)

    # --- 2. Adaptive threshold ---
    #     blockSize adapts: larger images → larger blocks
    block = max(9, min(17, short_side // 80)) | 1  # always odd
    C_val = 3 if (hi - lo) > 120 else 2

    edges = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        blockSize=block,
        C=C_val,
    )

    # --- 3. Remove fine noise (morphological opening) ---
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    edges = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel, iterations=1)

    # --- 4. Paper background (light gray) ---
    canvas_gray = np.clip(
        edges.astype(np.float32) * (220.0 / 255.0) + 28, 0, 248
    ).astype(np.uint8)

    canvas = cv2.cvtColor(canvas_gray, cv2.COLOR_GRAY2BGR)

    result.image = canvas
    result.description = "Contour sketch — thin pencil-style lines."
    return result
