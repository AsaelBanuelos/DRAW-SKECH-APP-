"""
RealSketch — Shading guide.

Generates a pedagogical visualization indicating which areas to shade,
with what intensity, and which areas to leave light.
"""

import cv2
import numpy as np
from typing import Optional

from app.models.result_models import FaceLandmarksResult, ShadingGuideResult


# Colors for shading zones (BGR)
COLOR_HIGHLIGHT = (200, 220, 255)    # Warm yellow — light zone
COLOR_MIDTONE = (150, 150, 150)      # Mid gray
COLOR_SHADOW = (70, 60, 55)          # Dark brown — shadow
COLOR_DEEP_SHADOW = (30, 25, 20)     # Near black — deep shadow
COLOR_ARROW = (100, 180, 255)        # Orange — stroke direction

ZONE_COLORS = {
    "light": (230, 235, 240),
    "mid": (155, 155, 155),
    "shadow": (75, 70, 65),
    "deep": (30, 28, 25),
}


def generate_shading_guide(
    image: np.ndarray,
    face_result: Optional[FaceLandmarksResult] = None,
) -> ShadingGuideResult:
    """
    Generate a pedagogical shading guide.

    Shows light, midtone, shadow and deep shadow zones
    in a clear and easy-to-interpret way.

    Args:
        image: Preprocessed BGR image.
        face_result: Face detection result (can be None).

    Returns:
        ShadingGuideResult with the visual guide.
    """
    result = ShadingGuideResult()
    h, w = image.shape[:2]

    # Step 1: Convert to grayscale and smooth
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 0)

    # Step 2: Enhance contrast (adaptive)
    lo, hi = int(np.percentile(gray, 2)), int(np.percentile(gray, 98))
    clip = 3.0 if (hi - lo) < 100 else 2.0
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Step 3: Classify each pixel into shading zones
    canvas = _create_shading_zones(gray, h, w)

    # Step 4: Add estimated light direction
    canvas = _draw_light_direction(canvas, gray, h, w)

    # Step 5: Add legend
    canvas = _draw_shading_legend(canvas)

    result.image = canvas
    result.description = (
        "Shading guide: light zones (leave white/light), "
        "midtones (soft shading), shadows (strong shading), "
        "and deep shadows (very dark shading)."
    )

    return result


def _create_shading_zones(
    gray: np.ndarray,
    h: int,
    w: int,
) -> np.ndarray:
    """Create an image with colored shading zones."""
    canvas = np.zeros((h, w, 3), dtype=np.uint8)

    # Define thresholds for 4 zones
    # Calculate percentiles to adapt to the image
    p25 = np.percentile(gray, 25)
    p50 = np.percentile(gray, 50)
    p75 = np.percentile(gray, 75)

    # Light zone (highlights)
    mask_light = gray >= p75
    canvas[mask_light] = ZONE_COLORS["light"]

    # Mid zone
    mask_mid = (gray >= p50) & (gray < p75)
    canvas[mask_mid] = ZONE_COLORS["mid"]

    # Shadow zone
    mask_shadow = (gray >= p25) & (gray < p50)
    canvas[mask_shadow] = ZONE_COLORS["shadow"]

    # Deep zone
    mask_deep = gray < p25
    canvas[mask_deep] = ZONE_COLORS["deep"]

    # Smooth edges between zones
    canvas = cv2.GaussianBlur(canvas, (5, 5), 0)

    return canvas


def _draw_light_direction(
    canvas: np.ndarray,
    gray: np.ndarray,
    h: int,
    w: int,
) -> np.ndarray:
    """
    Estimate the general light direction and draw an indicator arrow.

    Analyzes which quadrant has more brightness to estimate the light source.
    """
    # Divide into 9 sectors (3×3) for more precise light detection
    third_h, third_w = h // 3, w // 3
    sectors = {}
    positions = {}
    m = max(40, min(h, w) // 15)  # proportional margin
    for ri, rn in enumerate(["top", "mid", "bot"]):
        for ci, cn in enumerate(["left", "center", "right"]):
            r0, r1 = ri * third_h, (ri + 1) * third_h
            c0, c1 = ci * third_w, (ci + 1) * third_w
            sectors[f"{rn}_{cn}"] = float(np.mean(gray[r0:r1, c0:c1]))
            cx = c0 + third_w // 2
            cy = r0 + third_h // 2
            positions[f"{rn}_{cn}"] = (cx, cy)

    brightest = max(sectors, key=sectors.get)
    sx, sy = positions[brightest]

    # Arrow from brightest sector towards center
    center_x, center_y = w // 2, h // 2
    dx, dy = center_x - sx, center_y - sy
    length = max(1, (dx**2 + dy**2) ** 0.5)
    arrow_len = min(h, w) // 6
    start = (sx, sy)
    end = (sx + int(dx / length * arrow_len), sy + int(dy / length * arrow_len))

    thick = max(2, min(h, w) // 300)
    font_s = max(0.5, min(h, w) / 900)
    cv2.arrowedLine(canvas, start, end, COLOR_ARROW, thick, cv2.LINE_AA, tipLength=0.3)
    cv2.putText(canvas, "Light", (start[0] - int(12 * font_s), start[1] - int(12 * font_s)),
                cv2.FONT_HERSHEY_SIMPLEX, font_s, COLOR_ARROW, max(1, thick - 1), cv2.LINE_AA)

    return canvas


def _draw_shading_legend(canvas: np.ndarray) -> np.ndarray:
    """Draw a large, readable legend in the bottom-right corner."""
    h, w = canvas.shape[:2]

    labels_info = [
        ("Light (leave)", ZONE_COLORS["light"]),
        ("Mid (soft)", ZONE_COLORS["mid"]),
        ("Shadow (strong)", ZONE_COLORS["shadow"]),
        ("Deep (dense)", ZONE_COLORS["deep"]),
    ]

    n = len(labels_info)

    # Scale based on image size
    font_scale = max(0.7, min(h, w) / 800)
    thickness = max(1, round(font_scale * 1.5))
    box_w = int(34 * font_scale / 0.7)
    box_h = int(26 * font_scale / 0.7)
    row_gap = int(6 * font_scale / 0.7)
    padding = int(14 * font_scale / 0.7)

    # Measure widest text to calculate legend_w
    max_text_w = 0
    for label, _ in labels_info:
        (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX,
                                      font_scale, thickness)
        max_text_w = max(max_text_w, tw)

    legend_w = box_w + max_text_w + padding * 3 + 8
    legend_h = n * (box_h + row_gap) - row_gap + padding * 2

    # Position: bottom-right corner
    margin = int(12 * font_scale / 0.7)
    x_start = w - legend_w - margin
    y_start = h - legend_h - margin

    # Semi-transparent background
    overlay = canvas.copy()
    cv2.rectangle(overlay,
                  (x_start, y_start),
                  (x_start + legend_w, y_start + legend_h),
                  (25, 22, 20), -1)
    cv2.addWeighted(overlay, 0.85, canvas, 0.15, 0, canvas)
    cv2.rectangle(canvas,
                  (x_start, y_start),
                  (x_start + legend_w, y_start + legend_h),
                  (80, 80, 80), 1)

    for i, (label, color) in enumerate(labels_info):
        y = y_start + padding + i * (box_h + row_gap)
        x = x_start + padding

        cv2.rectangle(canvas, (x, y), (x + box_w, y + box_h), color, -1)
        cv2.rectangle(canvas, (x, y), (x + box_w, y + box_h), (100, 100, 100), 1)

        text_y = y + box_h - int(4 * font_scale / 0.7)
        cv2.putText(canvas, label,
                    (x + box_w + padding, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                    (220, 220, 220), thickness, cv2.LINE_AA)

    return canvas
