# ClearScale 1080p — Image Enhancer Application

A lightweight Python application with a minimalistic UI that upscales and enhances low-resolution images into crisp **Full HD 1080p** (`1920×1080`) images. Users can drag-and-drop or upload an image, choose an enhancement preset and framing mode, compare the original and enhanced 1080p output side-by-side, and download the result.

## Directory Structure

```text
image_enhancer_1080p/
├── start.py                  # Cross-platform Python start script (opens application)
├── start.bat                 # Windows one-click launcher
├── start.sh                  # macOS / Linux one-click launcher
├── main.py                   # Application entry point (Web UI, Desktop UI, & CLI)
├── config.py                 # Resolution targets, paths, and enhancement presets
├── requirements.txt          # Python package dependencies
├── README.md                 # Documentation and quick-start guide
├── enhancer/
│   ├── __init__.py
│   ├── pipeline.py           # 1080p super-resolution & restoration pipeline
│   └── utils.py              # Aspect-ratio calculators and file validators
├── ui/
│   ├── __init__.py
│   ├── web_server.py         # Minimalistic local web UI server (upload/enhance/download)
│   ├── desktop_app.py        # Native Tkinter desktop GUI option
│   ├── templates/
│   │   └── index.html        # Minimalistic responsive frontend
│   └── static/
│       ├── css/
│       │   └── style.css     # Clean, distraction-free stylesheet
│       └── js/
│           └── main.js       # Upload, side-by-side preview, and download controller
├── storage/
│   ├── uploads/              # Uploaded source images
│   └── outputs/              # Generated 1080p HD images
└── tests/
    ├── __init__.py
    └── test_enhancer.py      # Unit tests for 1080p upscaling and framing modes
```

## Quick Start

### 1. Install Dependencies (Automatic or Manual)
Running `start.py` checks for dependencies automatically, or you can install them manually:

```bash
pip install -r requirements.txt
```

### 2. Launch the Application
Use the start file for your operating system:

- **Cross-Platform (Python)**:
  ```bash
  python start.py
  ```
- **Windows**: Double-click `start.bat`
- **macOS / Linux**:
  ```bash
  ./start.sh
  ```

By default, the application starts a local server at `http://127.0.0.1:8080` and opens the minimalistic UI in your default browser.

### 3. Alternative Launch Modes
- **Native Desktop Window (Tkinter)**:
  ```bash
  python start.py --desktop
  ```
- **Direct Command-Line Enhancement**:
  ```bash
  python start.py --input path/to/lowres.jpg --output path/to/output_1080p.png --preset crisp
  ```

## Enhancement Pipeline Stages

1. **Edge-Preserving Pre-Denoising**: Bilateral filtering suppresses JPEG blockiness and chroma noise before scaling so artifacts are not magnified.
2. **Progressive Lanczos-4 Upscaling**: Stepwise interpolation (`cv2.INTER_LANCZOS4`) scales images smoothly toward 1080p (`1920×1080` landscape or `1080×1920` portrait) with intermediate edge refinement.
3. **LAB-Space Adaptive Local Contrast (CLAHE)**: Enhances local shadow and highlight detail strictly on the luminance (`L`) channel without shifting colors.
4. **Dual-Band Unsharp Masking & Vibrance**: Restores fine and medium-frequency edge crispness and exports in lossless PNG, 4:4:4 JPEG (95% quality), or WebP.
