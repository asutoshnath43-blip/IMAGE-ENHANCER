"""
Automated test suite for ClearScale 1080p Image Enhancer.
Verifies 1080p resolution scaling, aspect ratio modes, and pipeline output quality.
"""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from enhancer import ImageEnhancer1080p, EnhancementOptions, calculate_1080p_dimensions
from ui.web_server import generate_low_res_sample


class TestImageEnhancer1080p(unittest.TestCase):
    def setUp(self) -> None:
        self.enhancer = ImageEnhancer1080p()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_calculate_1080p_dimensions_landscape(self) -> None:
        # 16:9 low-res (480x270) -> exact 1920x1080
        w, h = calculate_1080p_dimensions(480, 270, "fit_1080p")
        self.assertEqual((w, h), (1920, 1080))

        # 4:3 low-res (640x480) -> 1440x1080
        w2, h2 = calculate_1080p_dimensions(640, 480, "fit_1080p")
        self.assertEqual((w2, h2), (1440, 1080))

    def test_calculate_1080p_dimensions_portrait(self) -> None:
        # 9:16 portrait (270x480) -> 1080x1920
        w, h = calculate_1080p_dimensions(270, 480, "fit_1080p")
        self.assertEqual((w, h), (1080, 1920))

    def test_enhance_sample_to_1080p(self) -> None:
        sample_in = self.work_path / "low_res_480x270.png"
        generate_low_res_sample(sample_in)
        out_file = self.work_path / "enhanced_1080p.png"

        opts = EnhancementOptions(preset="crisp", scaling_mode="fit_1080p", output_format="PNG")
        result = self.enhancer.enhance_file(sample_in, out_file, opts)

        self.assertTrue(out_file.exists())
        self.assertEqual(result.original_width, 480)
        self.assertEqual(result.original_height, 270)
        self.assertEqual(result.enhanced_width, 1920)
        self.assertEqual(result.enhanced_height, 1080)
        self.assertEqual(result.scale_factor, 4.0)

        with Image.open(out_file) as out_img:
            self.assertEqual(out_img.size, (1920, 1080))

    def test_exact_1920x1080_pad_and_crop_modes(self) -> None:
        # Create a square 300x300 low-res image
        sq_path = self.work_path / "square_300.png"
        Image.new("RGB", (300, 300), (60, 120, 200)).save(sq_path)

        pad_out = self.work_path / "padded_1080p.jpg"
        res_pad = self.enhancer.enhance_file(
            sq_path,
            pad_out,
            EnhancementOptions(scaling_mode="exact_1920x1080_pad", output_format="JPEG"),
        )
        self.assertEqual((res_pad.enhanced_width, res_pad.enhanced_height), (1920, 1080))

        crop_out = self.work_path / "cropped_1080p.webp"
        res_crop = self.enhancer.enhance_file(
            sq_path,
            crop_out,
            EnhancementOptions(scaling_mode="exact_1920x1080_crop", output_format="WEBP"),
        )
        self.assertEqual((res_crop.enhanced_width, res_crop.enhanced_height), (1920, 1080))


if __name__ == "__main__":
    unittest.main()
