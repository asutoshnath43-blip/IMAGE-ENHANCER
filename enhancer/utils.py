"""
Helper utilities for resolution calculation, file validation, and image metadata.
"""
from pathlib import Path
from typing import Tuple
from config import ALLOWED_EXTENSIONS, TARGET_WIDTH_FHD, TARGET_HEIGHT_FHD


def is_allowed_file(filename: str) -> bool:
    """Return True if the filename has a supported image extension."""
    if not filename:
        return False
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def calculate_1080p_dimensions(
    orig_width: int,
    orig_height: int,
    scaling_mode: str = "fit_1080p",
) -> Tuple[int, int]:
    """
    Calculate target 1080p dimensions based on input dimensions and scaling mode.

    Modes:
    - 'fit_1080p': Preserves exact aspect ratio while scaling up to Full HD 1080p class
                   (1920x1080 bounding box for landscape, 1080x1920 for portrait,
                   ensuring short side reaches 1080px unless constrained by 1920px max edge).
    - 'exact_1920x1080_pad': Exact 1920x1080 output with aspect-ratio preserved and ambient/studio pad.
    - 'exact_1920x1080_crop': Exact 1920x1080 output via smart center-fill crop.
    """
    if orig_width <= 0 or orig_height <= 0:
        raise ValueError("Image width and height must be positive integers.")

    if scaling_mode in ("exact_1920x1080_pad", "exact_1920x1080_crop"):
        return (TARGET_WIDTH_FHD, TARGET_HEIGHT_FHD)

    # Default 'fit_1080p': Preserve original aspect ratio
    is_landscape = orig_width >= orig_height
    max_long = TARGET_WIDTH_FHD   # 1920
    target_short = TARGET_HEIGHT_FHD  # 1080

    if is_landscape:
        # Scale so height = 1080; if width exceeds 1920, cap width at 1920
        scale = target_short / orig_height
        new_w = int(round(orig_width * scale))
        new_h = target_short
        if new_w > max_long:
            scale = max_long / orig_width
            new_w = max_long
            new_h = max(1, int(round(orig_height * scale)))
    else:
        # Portrait: Scale so width = 1080; if height exceeds 1920, cap height at 1920
        scale = target_short / orig_width
        new_w = target_short
        new_h = int(round(orig_height * scale))
        if new_h > max_long:
            scale = max_long / orig_height
            new_h = max_long
            new_w = max(1, int(round(orig_width * scale)))

    # Ensure even dimensions for standard 1080p compatibility
    new_w = new_w + (new_w % 2)
    new_h = new_h + (new_h % 2)
    return (new_w, new_h)
