"""
RealSketch — Export service.

Exports the processing results as individual PNG files
or in batch to a folder.
"""

import os
import cv2
import numpy as np
from typing import Optional, Dict
from datetime import datetime

from app.models.result_models import ProcessingResult


def export_single(
    image: np.ndarray,
    file_path: str,
) -> str:
    """
    Export a single image as PNG.

    Args:
        image: BGR numpy array image.
        file_path: Destination path.

    Returns:
        Path of the saved file.
    """
    # Ensure .png extension
    if not file_path.lower().endswith(".png"):
        file_path += ".png"

    # Create directory if it doesn't exist
    dir_path = os.path.dirname(file_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    # Save with OpenCV (supports unicode paths)
    ext = os.path.splitext(file_path)[1]
    result, encoded = cv2.imencode(ext, image)
    if result:
        encoded.tofile(file_path)
    else:
        raise IOError(f"Error encoding image for: {file_path}")

    return file_path


def export_all(
    result: ProcessingResult,
    output_dir: str,
) -> Dict[str, str]:
    """
    Export all results to a folder.

    Creates files with descriptive names:
    - 01_original.png
    - 02_sketch.png
    - 03_shading.png
    - 04_values.png

    Args:
        result: Complete processing result.
        output_dir: Destination directory.

    Returns:
        Dictionary {name: saved_path}.
    """
    os.makedirs(output_dir, exist_ok=True)

    exported = {}

    # Map results to file names
    exports_map = [
        ("01_original", result.original),
        ("02_sketch", result.sketch.image if result.sketch else None),
        ("03_shading", result.shading.image if result.shading else None),
        ("04_values", result.tone_map.image if result.tone_map else None),
    ]

    for name, image in exports_map:
        if image is not None:
            file_path = os.path.join(output_dir, f"{name}.png")
            try:
                export_single(image, file_path)
                exported[name] = file_path
            except Exception as e:
                print(f"[ExportService] Error exporting {name}: {e}")

    return exported


def get_default_export_dir() -> str:
    """Return the default export directory."""
    # Use 'exports' folder next to the executable
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    export_dir = os.path.join(base_dir, "exports")
    os.makedirs(export_dir, exist_ok=True)
    return export_dir


def generate_export_folder_name() -> str:
    """Generate a folder name based on date and time."""
    now = datetime.now()
    return now.strftime("realsketch_%Y%m%d_%H%M%S")
