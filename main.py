"""
Main entry point for ClearScale 1080p Image Enhancer.
Supports:
  - Interactive Web UI (default): `python main.py`
  - Native Tkinter Desktop UI:    `python main.py --desktop`
  - Direct CLI batch/file mode:   `python main.py --input lowres.jpg --output highres_1080p.png`
"""
import argparse
import sys
from pathlib import Path

from config import DEFAULT_HOST, DEFAULT_PORT, OUTPUT_DIR
from enhancer import ImageEnhancer1080p, EnhancementOptions
from ui.web_server import run_web_app
from ui.desktop_app import run_desktop_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ClearScale 1080p — Enhance low-resolution images to high-resolution 1080p."
    )
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="Launch the native Tkinter desktop GUI instead of the local browser UI.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Host address for web UI (default: {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port number for web UI (default: {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the web browser on startup.",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="Optional CLI mode: path to an input low-resolution image to enhance directly.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Optional CLI mode: destination path for the enhanced 1080p image.",
    )
    parser.add_argument(
        "--preset",
        choices=["balanced", "crisp", "photo_restore", "illustration"],
        default="balanced",
        help="Enhancement preset (default: balanced).",
    )
    parser.add_argument(
        "--scaling-mode",
        choices=["fit_1080p", "exact_1920x1080_pad", "exact_1920x1080_crop"],
        default="fit_1080p",
        help="1080p target framing mode (default: fit_1080p).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # CLI single-file mode if --input is provided
    if args.input:
        in_path = Path(args.input).resolve()
        if not in_path.exists():
            print(f"[Error] Input file not found: {in_path}", file=sys.stderr)
            return 1
        out_path = (
            Path(args.output).resolve()
            if args.output
            else OUTPUT_DIR / f"{in_path.stem}_1080p.png"
        )
        enhancer = ImageEnhancer1080p()
        options = EnhancementOptions(
            preset=args.preset,
            scaling_mode=args.scaling_mode,
            output_format=out_path.suffix.lstrip(".").upper() or "PNG",
        )
        res = enhancer.enhance_file(in_path, out_path, options)
        print(
            f"[Success] Enhanced {res.original_width}x{res.original_height} -> "
            f"{res.enhanced_width}x{res.enhanced_height} ({res.scale_factor}x) "
            f"in {res.processing_time_ms} ms."
        )
        print(f"[Saved] {res.output_path}")
        return 0

    if args.desktop:
        run_desktop_app()
    else:
        run_web_app(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
