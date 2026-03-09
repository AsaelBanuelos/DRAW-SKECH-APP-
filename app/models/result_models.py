"""
RealSketch — Data models for processing results.

Defines the structures that store the results from each stage
of the image analysis pipeline.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class FaceLandmarksResult:
    """Result of facial detection with MediaPipe."""
    detected: bool = False
    # Normalized key points (0-1) — scaled to actual image size when used
    landmarks: Optional[list] = None
    # Specific key points for drawing
    left_eye: Optional[tuple] = None
    right_eye: Optional[tuple] = None
    nose_tip: Optional[tuple] = None
    mouth_center: Optional[tuple] = None
    mouth_left: Optional[tuple] = None
    mouth_right: Optional[tuple] = None
    chin: Optional[tuple] = None
    forehead_top: Optional[tuple] = None
    jaw_left: Optional[tuple] = None
    jaw_right: Optional[tuple] = None
    face_oval: Optional[list] = None


@dataclass
class SketchResult:
    """Result of Sketch mode (pencil-style lines)."""
    image: Optional[np.ndarray] = None
    description: str = ""


@dataclass
class ToneMapResult:
    """Result of Tone Map mode."""
    image: Optional[np.ndarray] = None
    levels: int = 5
    description: str = ""


@dataclass
class ShadingGuideResult:
    """Result of Shading Guide mode."""
    image: Optional[np.ndarray] = None
    description: str = ""


@dataclass
class ProcessingResult:
    """Complete result of the processing pipeline."""
    original: Optional[np.ndarray] = None
    preprocessed: Optional[np.ndarray] = None
    face_landmarks: Optional[FaceLandmarksResult] = None
    sketch: Optional[SketchResult] = None
    tone_map: Optional[ToneMapResult] = None
    shading: Optional[ShadingGuideResult] = None
    has_face: bool = False
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Check if the result has at least the minimum data."""
        return self.original is not None and self.error is None
