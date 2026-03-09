# RealSketch 🎨

**Desktop application to convert photographs into realistic drawing guides.**

RealSketch analyzes an image and generates multiple visual aids so you can recreate it by hand on paper: contour sketch, tone map, and shading guide.

---

## Features

- **100% local** — no internet or backend required
- **Contour sketch** — clean pencil-style line drawing
- **Tone map** — image quantized into 4–5 light-to-shadow values
- **Shading guide** — light/dark zones with suggested intensity
- **Face detection** — if the image contains a face, generates specialized portrait guides
- **PNG export** — save each view as an independent image
- **PWA version** — runs 100% client-side in the browser (GitHub Pages)

---

## Requirements

- Python 3.11 or higher
- Windows 10/11

## Installation

```bash
# 1. Clone or download the project
cd real_sketch

# 2. Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

## Usage

1. Click **Load Image** and select a photograph (JPG, PNG, BMP, WEBP).
2. The image will appear in the left panel.
3. Click **Process** to analyze the image.
4. Navigate between the tabs in the right panel:
    - **Sketch** — clean pencil-style contour lines
    - **Shading** — light and shadow zones
    - **Values** — 4–5 level tone map
5. Click **Export** to save the results as PNG.

## Tech Stack

| Library   | Purpose                     |
| --------- | --------------------------- |
| PySide6   | Desktop graphical interface |
| OpenCV    | Image processing            |
| MediaPipe | Face and landmark detection |
| NumPy     | Matrix operations           |
| Pillow    | Image loading/saving        |

## Project Structure

```
real_sketch/
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
├── docs/                    # PWA version (GitHub Pages)
├── app/
│   ├── ui/                  # Graphical interface components
│   ├── controllers/         # Coordination logic
│   ├── services/            # Loading, exporting
│   ├── core/                # Image processing
│   └── models/              # Data models
├── assets/                  # Static resources
├── exports/                 # Output folder
└── tests/                   # Unit tests
```

## License

Personal and educational use.
