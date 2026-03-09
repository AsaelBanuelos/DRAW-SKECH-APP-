"""
RealSketch — Web server (Flask) for the PWA version.

Exposes the image processing pipeline as a REST API
and serves the frontend as a Progressive Web App.

Usage:
    python server.py
    → opens http://localhost:5000
"""

import os
import sys
import io
import base64
import traceback
import webbrowser
import threading

import cv2
import numpy as np
from flask import Flask, request, jsonify, send_from_directory

# Ensure path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.preprocess import preprocess_image
from app.core.face_landmarks import FaceLandmarkDetector
from app.core.sketch_generator import generate_sketch
from app.core.tone_mapper import generate_tone_map
from app.core.shading_guide import generate_shading_guide

# ---------------------------------------------------------------------------
# App Flask
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "web")

app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    static_url_path="",
)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB max


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _encode_image_b64(img: np.ndarray, fmt: str = ".png") -> str:
    """Encode a BGR numpy array to base64 data-URI."""
    ok, buf = cv2.imencode(fmt, img)
    if not ok:
        raise RuntimeError("Could not encode the image.")
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    mime = "image/png" if fmt == ".png" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def _decode_upload(file_storage) -> np.ndarray:
    """Read an uploaded file and decode it as a BGR image."""
    raw = file_storage.read()
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode the uploaded image.")
    return img


# ---------------------------------------------------------------------------
# Routes – Static files / PWA
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/manifest.json")
def manifest():
    return send_from_directory(STATIC_DIR, "manifest.json")


@app.route("/sw.js")
def service_worker():
    resp = send_from_directory(STATIC_DIR, "sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


# ---------------------------------------------------------------------------
# API – Processing
# ---------------------------------------------------------------------------

@app.route("/api/process", methods=["POST"])
def process_image():
    """
    Receive an image (multipart/form-data field "image"),
    execute the pipeline and return the 3 views as base64.
    """
    if "image" not in request.files:
        return jsonify({"error": "No image was sent."}), 400

    try:
        raw_img = _decode_upload(request.files["image"])
        preprocessed = preprocess_image(raw_img)

        # Face detection
        detector = FaceLandmarkDetector()
        try:
            face = detector.detect(preprocessed)
            has_face = face.detected
        finally:
            detector.close()

        # Pipeline
        sketch = generate_sketch(preprocessed)
        shading = generate_shading_guide(preprocessed, face)
        tone = generate_tone_map(preprocessed, levels=5)

        return jsonify({
            "ok": True,
            "has_face": has_face,
            "original": _encode_image_b64(preprocessed),
            "sketch": _encode_image_b64(sketch.image),
            "shading": _encode_image_b64(shading.image),
            "values": _encode_image_b64(tone.image),
        })

    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _open_browser():
    """Open the browser after a brief delay."""
    import time
    time.sleep(1.2)
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║   RealSketch PWA — http://localhost:5000 ║")
    print("╚══════════════════════════════════════════╝")
    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)
