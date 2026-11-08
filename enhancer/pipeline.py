"""
Core 1080p Super-Resolution and Image Quality Enhancement Pipeline.
Combines multi-step Lanczos-4 interpolation, bilateral/NLM artifact removal,
LAB-space CLAHE local contrast restoration, and frequency-tuned unsharp masking.
"""
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from config import PRESETS, TARGET_WIDTH_FHD, TARGET_HEIGHT_FHD
from .utils import calculate_1080p_dimensions


@dataclass
class EnhancementOptions:
    preset: str = "balanced"
    scaling_mode: str = "fit_1080p"  # 'fit_1080p', 'exact_1920x1080_pad', 'exact_1920x1080_crop'
    output_format: str = "PNG"       # 'PNG', 'JPEG', 'WEBP'
    jpeg_quality: int = 95
    custom_sharpen: Optional[float] = None
    custom_denoise: Optional[float] = None
    custom_contrast: Optional[float] = None


@dataclass
class EnhancementResult:
    output_path: str
    output_filename: str
    original_width: int
    original_height: int
    enhanced_width: int
    enhanced_height: int
    scale_factor: float
    processing_time_ms: int
    preset_used: str
    scaling_mode: str
    output_format: str
    file_size_kb: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ImageEnhancer1080p:
    """
    High-precision 1080p image upscaler and enhancer.
    Uses OpenCV + Pillow when available, with automatic fallback to pure Pillow.
    """

    def __init__(self) -> None:
        self.has_opencv = HAS_OPENCV

    def enhance_file(
        self,
        input_path: Path,
        output_path: Path,
        options: Optional[EnhancementOptions] = None,
    ) -> EnhancementResult:
        """Load an image from disk, enhance it to 1080p, and save to output_path."""
        if options is None:
            options = EnhancementOptions()

        start_time = time.perf_counter()

        with Image.open(input_path) as img:
            orig_w, orig_h = img.size
            enhanced_img = self.enhance_pil_image(img, options)

        enhanced_w, enhanced_h = enhanced_img.size
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fmt = options.output_format.upper()
        if fmt == "JPG":
            fmt = "JPEG"

        save_kwargs: Dict[str, Any] = {}
        if fmt in ("JPEG", "WEBP"):
            if enhanced_img.mode in ("RGBA", "LA", "P"):
                # Composite transparency over studio dark/white background for JPEG
                bg = Image.new("RGB", enhanced_img.size, (255, 255, 255))
                if enhanced_img.mode == "P":
                    enhanced_img = enhanced_img.convert("RGBA")
                bg.paste(enhanced_img, mask=enhanced_img.split()[-1])
                enhanced_img = bg
            else:
                enhanced_img = enhanced_img.convert("RGB")
            save_kwargs["quality"] = max(70, min(100, options.jpeg_quality))
            if fmt == "JPEG":
                save_kwargs["subsampling"] = 0  # 4:4:4 chroma for maximum 1080p sharpness
                save_kwargs["optimize"] = True
        else:
            fmt = "PNG"
            save_kwargs["optimize"] = True

        enhanced_img.save(output_path, format=fmt, **save_kwargs)

        elapsed_ms = int(round((time.perf_counter() - start_time) * 1000))
        scale_factor = round(
            max(enhanced_w / max(1, orig_w), enhanced_h / max(1, orig_h)), 2
        )
        size_kb = round(output_path.stat().st_size / 1024.0, 1)

        return EnhancementResult(
            output_path=str(output_path),
            output_filename=output_path.name,
            original_width=orig_w,
            original_height=orig_h,
            enhanced_width=enhanced_w,
            enhanced_height=enhanced_h,
            scale_factor=scale_factor,
            processing_time_ms=elapsed_ms,
            preset_used=options.preset,
            scaling_mode=options.scaling_mode,
            output_format=fmt,
            file_size_kb=size_kb,
        )

    def enhance_pil_image(
        self,
        img: Image.Image,
        options: Optional[EnhancementOptions] = None,
    ) -> Image.Image:
        """Enhance a PIL.Image instance to 1080p resolution."""
        if options is None:
            options = EnhancementOptions()

        preset_cfg = dict(PRESETS.get(options.preset, PRESETS["balanced"]))
        if options.custom_sharpen is not None:
            preset_cfg["sharpen_amount"] = float(options.custom_sharpen)
        if options.custom_denoise is not None:
            preset_cfg["denoise_strength"] = float(options.custom_denoise)
        if options.custom_contrast is not None:
            preset_cfg["clahe_clip"] = float(options.custom_contrast)

        # Preserve alpha channel if present
        has_alpha = img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        )
        if has_alpha:
            rgba = img.convert("RGBA")
            rgb_img = Image.merge("RGB", rgba.split()[:3])
            alpha_channel = rgba.split()[3]
        else:
            rgb_img = img.convert("RGB")
            alpha_channel = None

        orig_w, orig_h = rgb_img.size
        fit_w, fit_h = calculate_1080p_dimensions(orig_w, orig_h, "fit_1080p")

        if self.has_opencv:
            enhanced_rgb = self._enhance_with_opencv(
                rgb_img, (fit_w, fit_h), preset_cfg
            )
        else:
            enhanced_rgb = self._enhance_with_pillow(
                rgb_img, (fit_w, fit_h), preset_cfg
            )

        if alpha_channel is not None:
            upscaled_alpha = alpha_channel.resize(
                enhanced_rgb.size, Image.Resampling.LANCZOS
            )
            enhanced_rgb = enhanced_rgb.convert("RGBA")
            enhanced_rgb.putalpha(upscaled_alpha)

        # Apply framing mode if exact 1920x1080 was requested
        if options.scaling_mode == "exact_1920x1080_pad":
            enhanced_rgb = self._apply_smart_1080p_pad(
                enhanced_rgb, (TARGET_WIDTH_FHD, TARGET_HEIGHT_FHD)
            )
        elif options.scaling_mode == "exact_1920x1080_crop":
            enhanced_rgb = self._apply_smart_1080p_crop(
                enhanced_rgb, (TARGET_WIDTH_FHD, TARGET_HEIGHT_FHD)
            )

        return enhanced_rgb

    def _enhance_with_opencv(
        self,
        rgb_img: Image.Image,
        target_size: Tuple[int, int],
        cfg: Dict[str, Any],
    ) -> Image.Image:
        """OpenCV multi-stage super-resolution and restoration pipeline."""
        target_w, target_h = target_size
        arr = np.array(rgb_img, dtype=np.uint8)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        # Stage 1: Edge-preserving denoise on low-res source to remove compression blockiness
        denoise_str = float(cfg.get("denoise_strength", 3.5))
        if denoise_str > 0.5:
            d_sigma_color = min(45.0, denoise_str * 5.0)
            d_sigma_space = min(15.0, denoise_str * 1.5)
            bgr = cv2.bilateralFilter(
                bgr, d=5, sigmaColor=d_sigma_color, sigmaSpace=d_sigma_space
            )

        # Stage 2: Progressive / Stepwise Lanczos-4 Upscaling
        # Upscaling in max 2x steps with intermediate light edge sharpening yields cleaner gradients
        cur_h, cur_w = bgr.shape[:2]
        while cur_w * 1.8 < target_w and cur_h * 1.8 < target_h:
            cur_w = min(target_w, int(round(cur_w * 1.8)))
            cur_h = min(target_h, int(round(cur_h * 1.8)))
            bgr = cv2.resize(bgr, (cur_w, cur_h), interpolation=cv2.INTER_LANCZOS4)
            # Subtle intermediate unsharp pass
            blur_mid = cv2.GaussianBlur(bgr, (0, 0), sigmaX=0.9)
            bgr = cv2.addWeighted(bgr, 1.18, blur_mid, -0.18, 0)

        if (cur_w, cur_h) != (target_w, target_h):
            bgr = cv2.resize(
                bgr, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4
            )

        # Stage 3: Adaptive Local Contrast Enhancement (CLAHE in LAB Luminance channel)
        clahe_clip = float(cfg.get("clahe_clip", 1.6))
        if clahe_clip > 0.1:
            lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
            l_chan, a_chan, b_chan = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l_chan)
            # Blend 55% CLAHE luminance with 45% original luminance for natural tonal transitions
            l_blended = cv2.addWeighted(l_enhanced, 0.55, l_chan, 0.45, 0)
            lab_merged = cv2.merge((l_blended, a_chan, b_chan))
            bgr = cv2.cvtColor(lab_merged, cv2.COLOR_LAB2BGR)

        # Stage 4: Optional OpenCV Detail Enhance for ultra-crisp preset
        if cfg.get("detail_enhance", False):
            detail = cv2.detailEnhance(bgr, sigma_s=8, sigma_r=0.12)
            bgr = cv2.addWeighted(bgr, 0.72, detail, 0.28, 0)

        # Stage 5: Frequency-Separated Unsharp Masking (Fine + Medium Radius)
        sharpen_amount = float(cfg.get("sharpen_amount", 1.15))
        if sharpen_amount > 0.05:
            fine_blur = cv2.GaussianBlur(bgr, (0, 0), sigmaX=1.1)
            med_blur = cv2.GaussianBlur(bgr, (0, 0), sigmaX=2.4)
            fine_weight = 0.65 * sharpen_amount
            med_weight = 0.25 * sharpen_amount
            base_weight = 1.0 + fine_weight + med_weight
            bgr = cv2.addWeighted(bgr, base_weight, fine_blur, -fine_weight, 0)
            bgr = cv2.addWeighted(bgr, 1.0, med_blur, -med_weight, 0)

        rgb_out = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil_out = Image.fromarray(rgb_out)

        # Stage 6: Subtle Color Vibrance Boost
        color_boost = float(cfg.get("color_boost", 1.06))
        if abs(color_boost - 1.0) > 0.01:
            pil_out = ImageEnhance.Color(pil_out).enhance(color_boost)

        return pil_out

    def _enhance_with_pillow(
        self,
        rgb_img: Image.Image,
        target_size: Tuple[int, int],
        cfg: Dict[str, Any],
    ) -> Image.Image:
        """Fallback pure-Pillow 1080p enhancement pipeline."""
        out = rgb_img.resize(target_size, Image.Resampling.LANCZOS)
        sharpen_amount = float(cfg.get("sharpen_amount", 1.15))
        percent = int(round(110 * sharpen_amount))
        out = out.filter(ImageFilter.UnsharpMask(radius=1.6, percent=percent, threshold=2))
        out = ImageEnhance.Contrast(out).enhance(1.06)
        out = ImageEnhance.Color(out).enhance(float(cfg.get("color_boost", 1.05)))
        return out

    def _apply_smart_1080p_pad(
        self, img: Image.Image, target_fhd: Tuple[int, int]
    ) -> Image.Image:
        """
        Places an image onto a 1920x1080 canvas with an ambient blurred background
        so the output is strictly 1920x1080 without cropping or stretching.
        """
        tw, th = target_fhd
        iw, ih = img.size
        scale = min(tw / iw, th / ih)
        nw = max(1, int(round(iw * scale)))
        nh = max(1, int(round(ih * scale)))
        fg = img.resize((nw, nh), Image.Resampling.LANCZOS)

        if (nw, nh) == (tw, th):
            return fg

        # Create ambient blurred 1920x1080 background from the image itself
        bg = img.convert("RGB").resize((tw, th), Image.Resampling.BICUBIC)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=36))
        bg = ImageEnhance.Brightness(bg).enhance(0.45)

        if img.mode == "RGBA":
            bg = bg.convert("RGBA")
            offset = ((tw - nw) // 2, (th - nh) // 2)
            bg.paste(fg, offset, mask=fg.split()[3])
        else:
            offset = ((tw - nw) // 2, (th - nh) // 2)
            bg.paste(fg, offset)

        return bg

    def _apply_smart_1080p_crop(
        self, img: Image.Image, target_fhd: Tuple[int, int]
    ) -> Image.Image:
        """Scales and center-crops the image to fill an exact 1920x1080 frame."""
        tw, th = target_fhd
        iw, ih = img.size
        scale = max(tw / iw, th / ih)
        nw = max(tw, int(round(iw * scale)))
        nh = max(th, int(round(ih * scale)))
        scaled = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - tw) // 2
        top = (nh - th) // 2
        return scaled.crop((left, top, left + tw, top + th))
