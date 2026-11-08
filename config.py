"""
Configuration constants and default presets for the 1080p Image Enhancer Application.
"""
import os
from pathlib import Path

APP_NAME = "ClearScale 1080p — Image Enhancer"
APP_VERSION = "1.0.0"

# Base directories
ROOT_DIR = Path(__file__).resolve().parent
STORAGE_DIR = ROOT_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"

# Ensure storage directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Server settings
DEFAULT_HOST = os.environ.get("ENHANCER_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("ENHANCER_PORT", "8080"))
MAX_UPLOAD_SIZE_MB = 32
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}

# Target 1080p Resolution Standards
TARGET_WIDTH_FHD = 1920
TARGET_HEIGHT_FHD = 1080

# Enhancement Presets
PRESETS = {
    "balanced": {
        "label": "Balanced HD (Recommended)",
        "description": "Natural detail recovery, adaptive contrast, and subtle noise reduction.",
        "denoise_strength": 3.5,
        "sharpen_amount": 1.15,
        "clahe_clip": 1.6,
        "color_boost": 1.06,
        "detail_enhance": False,
    },
    "crisp": {
        "label": "Ultra Crisp & Sharp",
        "description": "Strong edge definition and micro-contrast for architecture, text, and product shots.",
        "denoise_strength": 2.0,
        "sharpen_amount": 1.65,
        "clahe_clip": 2.1,
        "color_boost": 1.05,
        "detail_enhance": True,
    },
    "photo_restore": {
        "label": "Low-Light / Noisy Photo",
        "description": "Higher artifact & noise suppression with gentle sharpening for compressed JPEGs.",
        "denoise_strength": 7.0,
        "sharpen_amount": 0.95,
        "clahe_clip": 1.8,
        "color_boost": 1.08,
        "detail_enhance": False,
    },
    "illustration": {
        "label": "Digital Art & Illustration",
        "description": "Edge-preserving smoothing with clean lines and vibrant colors.",
        "denoise_strength": 5.5,
        "sharpen_amount": 1.35,
        "clahe_clip": 1.3,
        "color_boost": 1.14,
        "detail_enhance": False,
    },
}
