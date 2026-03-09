"""
RealSketch — Tone map.

Converts the image to a quantized grayscale with 4–5 levels
to clearly visualize light and shadow zones.
"""

import cv2
import numpy as np

from app.models.result_models import ToneMapResult


# Names for each tonal level
TONE_LABELS = ["Light", "Mid-light", "Midtone", "Shadow", "Deep"]

# Colors for the legend (grayscale)
TONE_VALUES_5 = [230, 180, 130, 75, 25]
TONE_VALUES_4 = [230, 170, 100, 30]


def generate_tone_map(
    image: np.ndarray,
    levels: int = 5,
) -> ToneMapResult:
    """
    Generate a quantized tone map of the image.

    Converts the image to grayscale, enhances contrast
    and quantizes to N tonal levels.

    Args:
        image: Preprocessed BGR image.
        levels: Number of tonal levels (4 or 5).

    Returns:
        ToneMapResult with the tonal image.
    """
    result = ToneMapResult()
    result.levels = levels
    h, w = image.shape[:2]

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Enhance contrast with CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Slightly smooth to remove noise
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Quantize to N levels
    tone_values = TONE_VALUES_5 if levels == 5 else TONE_VALUES_4
    active_labels = TONE_LABELS[:levels] if levels == 5 else TONE_LABELS[:4]

    quantized = _quantize_tones(gray, levels, tone_values)

    # Convert to BGR for consistent display
    canvas = cv2.cvtColor(quantized, cv2.COLOR_GRAY2BGR)

    # Add legend
    canvas = _draw_tone_legend(canvas, tone_values, active_labels)

    result.image = canvas
    result.description = f"Tone map with {levels} levels: {', '.join(active_labels)}."

    return result


def _quantize_tones(
    gray: np.ndarray,
    levels: int,
    tone_values: list,
) -> np.ndarray:
    """Quantize a grayscale image to N tonal levels.

    Uses percentiles instead of fixed thresholds to adapt
    to the actual dynamic range of each image.
    """
    quantized = np.zeros_like(gray)

    # Adaptive percentiles → works well with B&W, low contrast, etc.
    pcts = np.linspace(0, 100, levels + 1)
    thresholds = [np.percentile(gray, p) for p in pcts]

    for i in range(levels):
        lower = thresholds[i]
        upper = thresholds[i + 1] if i < levels - 1 else 256

        mask = (gray >= lower) & (gray < upper)
        quantized[mask] = tone_values[levels - 1 - i]

    return quantized


def _draw_tone_legend(
    canvas: np.ndarray,
    tone_values: list,
    labels: list,
) -> np.ndarray:
    """Draw a large, readable legend in the bottom-right corner."""
    h, w = canvas.shape[:2]
    n = len(tone_values)

    # Scaled dimensions for good readability
    font_scale = max(0.7, min(h, w) / 800)      # scales with the image
    thickness = max(1, round(font_scale * 1.5))
    box_w = int(34 * font_scale / 0.7)
    box_h = int(26 * font_scale / 0.7)
    row_gap = int(6 * font_scale / 0.7)
    padding = int(14 * font_scale / 0.7)

    # Measure widest text to calculate legend_w
    max_text_w = 0
    for label in labels:
        (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX,
                                      font_scale, thickness)
        max_text_w = max(max_text_w, tw)

    legend_w = box_w + max_text_w + padding * 3 + 8
    legend_h = n * (box_h + row_gap) - row_gap + padding * 2

    # Position: bottom-right corner (always)
    margin = int(12 * font_scale / 0.7)
    x_start = w - legend_w - margin
    y_start = h - legend_h - margin

    # Semi-transparent background
    overlay = canvas.copy()
    cv2.rectangle(overlay,
                  (x_start, y_start),
                  (x_start + legend_w, y_start + legend_h),
                  (30, 28, 25), -1)
    cv2.addWeighted(overlay, 0.85, canvas, 0.15, 0, canvas)
    cv2.rectangle(canvas,
                  (x_start, y_start),
                  (x_start + legend_w, y_start + legend_h),
                  (100, 100, 100), 1)

    # Draw each level
    for i, (val, label) in enumerate(zip(tone_values, labels)):
        y = y_start + padding + i * (box_h + row_gap)
        x = x_start + padding

        # Color box
        cv2.rectangle(canvas, (x, y), (x + box_w, y + box_h),
                      (val, val, val), -1)
        cv2.rectangle(canvas, (x, y), (x + box_w, y + box_h),
                      (120, 120, 120), 1)

        # Large readable text
        text_y = y + box_h - int(4 * font_scale / 0.7)
        cv2.putText(canvas, label,
                    (x + box_w + padding, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                    (220, 220, 220), thickness, cv2.LINE_AA)

    return canvas
