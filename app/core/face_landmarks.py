"""
RealSketch — Facial landmark detection.

Hybrid strategy:
1. Tries MediaPipe (legacy mp.solutions API or new tasks API).
2. If MediaPipe is not available or fails, uses OpenCV Haar Cascade
   with landmark estimation based on standard facial proportions.

If no face is found, returns an empty result without error.
"""

import os
import cv2
import numpy as np
from typing import Optional, Tuple, List

from app.models.result_models import FaceLandmarksResult


# ============================================================================
# MediaPipe Face Mesh indices (used only if MediaPipe works)
# ============================================================================
FACE_OVAL_INDICES = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 10
]
LEFT_EYE_INDICES = [33, 133]
RIGHT_EYE_INDICES = [362, 263]
NOSE_TIP = 1
MOUTH_LEFT = 61
MOUTH_RIGHT = 291
MOUTH_TOP = 13
MOUTH_BOTTOM = 14
CHIN = 152
FOREHEAD = 10
JAW_LEFT = 234
JAW_RIGHT = 454


# ============================================================================
# Try to import MediaPipe (may not be available or incompatible version)
# ============================================================================
_MEDIAPIPE_AVAILABLE = False
_mp_face_mesh_class = None

try:
    import mediapipe as mp
    # API legacy (mediapipe <= 0.10.14 approx.)
    _face_mesh_mod = getattr(mp, "solutions", None)
    if _face_mesh_mod is not None:
        _mp_face_mesh_class = _face_mesh_mod.face_mesh.FaceMesh
        _MEDIAPIPE_AVAILABLE = True
except Exception:
    pass

if not _MEDIAPIPE_AVAILABLE:
    try:
        # Alternative attempt: direct import of submodule
        from mediapipe.python.solutions import face_mesh as _fm_module  # type: ignore
        _mp_face_mesh_class = _fm_module.FaceMesh
        _MEDIAPIPE_AVAILABLE = True
    except Exception:
        pass


# ============================================================================
# Main detector (facade)
# ============================================================================
class FaceLandmarkDetector:
    """
    Detects facial landmarks.

    Uses MediaPipe if available; otherwise falls back to
    OpenCV Haar Cascade + standard anatomical proportions.
    """

    def __init__(self):
        self._backend: str = "none"
        self._mp_mesh = None
        self._cascade = None

        if _MEDIAPIPE_AVAILABLE and _mp_face_mesh_class is not None:
            try:
                self._mp_mesh = _mp_face_mesh_class(
                    static_image_mode=True,
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                )
                self._backend = "mediapipe"
            except Exception:
                self._mp_mesh = None

        # Fallback: Haar Cascade (included in OpenCV)
        if self._backend != "mediapipe":
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._cascade = cv2.CascadeClassifier(cascade_path)
            if self._cascade.empty():
                # Alternate path attempt
                alt = cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
                self._cascade = cv2.CascadeClassifier(alt)
            self._backend = "opencv"

    # ------------------------------------------------------------------
    def detect(self, image: np.ndarray) -> FaceLandmarksResult:
        """Detect facial landmarks in the image."""
        if self._backend == "mediapipe" and self._mp_mesh is not None:
            return self._detect_mediapipe(image)
        return self._detect_opencv(image)

    # ------------------------------------------------------------------
    # MediaPipe path
    # ------------------------------------------------------------------
    def _detect_mediapipe(self, image: np.ndarray) -> FaceLandmarksResult:
        result = FaceLandmarksResult()
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]

        try:
            detections = self._mp_mesh.process(rgb)
        except Exception:
            # If MediaPipe fails at runtime, fall back to OpenCV
            return self._detect_opencv(image)

        if not detections or not detections.multi_face_landmarks:
            return result

        face_lm = detections.multi_face_landmarks[0]
        result.detected = True

        def px(index: int) -> Tuple[int, int]:
            lm = face_lm.landmark[index]
            return (int(lm.x * w), int(lm.y * h))

        def px_mid(i1: int, i2: int) -> Tuple[int, int]:
            p1, p2 = px(i1), px(i2)
            return ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)

        result.landmarks = [(int(lm.x * w), int(lm.y * h)) for lm in face_lm.landmark]
        result.left_eye = px_mid(*LEFT_EYE_INDICES)
        result.right_eye = px_mid(*RIGHT_EYE_INDICES)
        result.nose_tip = px(NOSE_TIP)
        result.mouth_center = px_mid(MOUTH_TOP, MOUTH_BOTTOM)
        result.mouth_left = px(MOUTH_LEFT)
        result.mouth_right = px(MOUTH_RIGHT)
        result.chin = px(CHIN)
        result.forehead_top = px(FOREHEAD)
        result.jaw_left = px(JAW_LEFT)
        result.jaw_right = px(JAW_RIGHT)
        result.face_oval = [px(i) for i in FACE_OVAL_INDICES]

        return result

    # ------------------------------------------------------------------
    # OpenCV Haar Cascade + proporciones anatómicas
    # ------------------------------------------------------------------
    def _detect_opencv(self, image: np.ndarray) -> FaceLandmarksResult:
        """
        Detect face with Haar Cascade and estimate landmarks using
        standard facial proportions (classic portrait canon):
          - Eyes at ~45% of face height
          - Nose at ~70%
          - Mouth at ~82%
          - Chin at ~100%
        """
        result = FaceLandmarksResult()

        if self._cascade is None or self._cascade.empty():
            return result

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = self._cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )

        if len(faces) == 0:
            return result

        # Take the largest face
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        fx, fy, fw, fh = faces[0]

        result.detected = True

        # Face center
        cx = fx + fw // 2
        cy = fy + fh // 2

        # Landmarks estimated by proportion
        eye_y = fy + int(fh * 0.38)
        eye_sep = int(fw * 0.30)
        result.left_eye = (cx - eye_sep, eye_y)
        result.right_eye = (cx + eye_sep, eye_y)

        nose_y = fy + int(fh * 0.62)
        result.nose_tip = (cx, nose_y)

        mouth_y = fy + int(fh * 0.78)
        mouth_hw = int(fw * 0.22)
        result.mouth_center = (cx, mouth_y)
        result.mouth_left = (cx - mouth_hw, mouth_y)
        result.mouth_right = (cx + mouth_hw, mouth_y)

        result.chin = (cx, fy + fh)
        result.forehead_top = (cx, fy)
        result.jaw_left = (fx, fy + int(fh * 0.75))
        result.jaw_right = (fx + fw, fy + int(fh * 0.75))

        # Generate approximate facial oval (ellipse)
        result.face_oval = _generate_oval_points(cx, cy, fw, fh)

        return result

    # ------------------------------------------------------------------
    def close(self):
        """Release resources."""
        if self._mp_mesh is not None:
            try:
                self._mp_mesh.close()
            except Exception:
                pass


def _generate_oval_points(
    cx: int, cy: int, w: int, h: int, n_points: int = 36
) -> List[Tuple[int, int]]:
    """Generate points of an oval (ellipse) to simulate the facial contour."""
    points = []
    a = w // 2       # horizontal semi-axis
    b = int(h * 0.52)  # vertical semi-axis (face slightly taller)
    for i in range(n_points):
        angle = 2 * np.pi * i / n_points
        x = int(cx + a * np.cos(angle))
        y = int(cy + b * np.sin(angle))
        points.append((x, y))
    points.append(points[0])  # Close the oval
    return points
