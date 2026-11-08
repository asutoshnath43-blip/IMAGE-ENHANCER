"""
Zero-dependency Python HTTP Web Server for the 1080p Image Enhancer UI.
Handles static files, multipart image upload, sample image generation,
1080p enhancement execution, and file download.
"""
import email.parser
import json
import mimetypes
import shutil
import threading
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urlparse, parse_qs

from PIL import Image, ImageDraw

from config import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    UPLOAD_DIR,
    OUTPUT_DIR,
    MAX_UPLOAD_SIZE_MB,
)
from enhancer import ImageEnhancer1080p, EnhancementOptions, is_allowed_file

UI_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = UI_DIR / "templates"
STATIC_DIR = UI_DIR / "static"

ENHANCER = ImageEnhancer1080p()


def generate_low_res_sample(target_path: Path) -> Path:
    """Generate a colorful, detailed 480x270 low-res sample image for instant testing."""
    w, h = 480, 270
    img = Image.new("RGB", (w, h), (18, 28, 48))
    draw = ImageDraw.Draw(img)

    # Sky gradient & geometric mountain/horizon test pattern
    for y in range(h):
        r = int(20 + (y / h) * 85)
        g = int(35 + (y / h) * 110)
        b = int(75 + (y / h) * 140)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Sun disc
    draw.ellipse([320, 42, 395, 117], fill=(252, 211, 77), outline=(254, 243, 199), width=2)

    # Stylized mountains
    draw.polygon([(0, 220), (130, 105), (270, 220)], fill=(30, 58, 95))
    draw.polygon([(160, 225), (300, 95), (460, 225)], fill=(45, 82, 126))
    draw.polygon([(270, 235), (390, 130), (480, 235)], fill=(23, 43, 77))

    # Foreground architectural grid & crisp resolution bars
    draw.rectangle([0, 220, w, h], fill=(15, 23, 42))
    for x in range(20, w - 20, 24):
        draw.rectangle([x, 232, x + 12, 256], fill=(56, 189, 248))

    draw.rectangle([22, 22, 215, 68], fill=(15, 23, 42), outline=(148, 163, 184), width=1)
    draw.text((34, 32), "LOW-RES INPUT (480x270)", fill=(248, 250, 252))
    draw.text((34, 48), "Upscale -> 1920x1080 HD", fill=(56, 189, 248))

    target_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(target_path, format="PNG")
    return target_path


def parse_multipart_form_data(
    body: bytes, content_type: str
) -> Tuple[Dict[str, str], Optional[Tuple[str, bytes]]]:
    """
    Parse multipart/form-data request body using Python standard library `email.parser`.
    Returns (fields_dict, (filename, file_bytes) or None).
    """
    header_bytes = f"Content-Type: {content_type}\r\n\r\n".encode("utf-8")
    msg = email.parser.BytesParser().parsebytes(header_bytes + body)

    fields: Dict[str, str] = {}
    uploaded_file: Optional[Tuple[str, bytes]] = None

    if msg.is_multipart():
        for part in msg.iter_parts():
            disposition = part.get_content_disposition()
            if disposition != "form-data":
                continue
            name = part.get_param("name", header="content-disposition")
            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            if filename:
                uploaded_file = (filename, payload)
            elif name:
                fields[name] = payload.decode("utf-8", errors="replace")

    return fields, uploaded_file


class EnhancerHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler serving the minimalistic UI and enhancement API."""

    def log_message(self, format: str, *args: Any) -> None:
        # Keep console output clean and minimal
        pass

    def _send_json(self, payload: Dict[str, Any], status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(
        self, file_path: Path, as_download: bool = False, download_name: Optional[str] = None
    ) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(data)))
        if as_download:
            dl_name = download_name or file_path.name
            self.send_header(
                "Content-Disposition", f'attachment; filename="{dl_name}"'
            )
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        query = parse_qs(parsed.query)

        if route in ("/", "/index.html"):
            self._serve_file(TEMPLATE_DIR / "index.html")
            return

        if route.startswith("/static/"):
            rel = route[len("/static/"):]
            target = (STATIC_DIR / rel).resolve()
            if str(target).startswith(str(STATIC_DIR.resolve())):
                self._serve_file(target)
                return
            self.send_error(HTTPStatus.FORBIDDEN)
            return

        if route.startswith("/uploads/"):
            rel = Path(route).name
            self._serve_file(UPLOAD_DIR / rel)
            return

        if route.startswith("/outputs/"):
            rel = Path(route).name
            as_dl = query.get("download", ["0"])[0] == "1"
            self._serve_file(OUTPUT_DIR / rel, as_download=as_dl, download_name=rel)
            return

        if route == "/api/health":
            self._send_json({"status": "ok", "opencv_enabled": ENHANCER.has_opencv})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/enhance":
            self._send_json({"error": "Unknown API endpoint"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
            if content_length <= 0 or content_length > max_bytes:
                self._send_json(
                    {"error": f"Upload size must be between 1B and {MAX_UPLOAD_SIZE_MB}MB."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            content_type = self.headers.get("Content-Type", "")
            body = self.rfile.read(content_length)
            fields, uploaded = parse_multipart_form_data(body, content_type)

            job_id = uuid.uuid4().hex[:10]
            use_sample = fields.get("use_sample") == "1"

            if use_sample:
                in_filename = f"sample_{job_id}.png"
                in_path = UPLOAD_DIR / in_filename
                generate_low_res_sample(in_path)
            else:
                if not uploaded:
                    self._send_json(
                        {"error": "Please select an image file to upload."},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                orig_name, file_bytes = uploaded
                if not is_allowed_file(orig_name):
                    self._send_json(
                        {"error": "Unsupported file type. Upload PNG, JPG, WEBP, BMP, or TIFF."},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                ext = Path(orig_name).suffix.lower()
                in_filename = f"upload_{job_id}{ext}"
                in_path = UPLOAD_DIR / in_filename
                in_path.write_bytes(file_bytes)

            preset = fields.get("preset", "balanced")
            scaling_mode = fields.get("scaling_mode", "fit_1080p")
            output_format = fields.get("output_format", "PNG").upper()
            sharpen_str = fields.get("sharpen")
            custom_sharpen = float(sharpen_str) if sharpen_str else None

            ext_map = {"PNG": ".png", "JPEG": ".jpg", "JPG": ".jpg", "WEBP": ".webp"}
            out_ext = ext_map.get(output_format, ".png")
            out_filename = f"enhanced_1080p_{job_id}{out_ext}"
            out_path = OUTPUT_DIR / out_filename

            options = EnhancementOptions(
                preset=preset,
                scaling_mode=scaling_mode,
                output_format=output_format,
                custom_sharpen=custom_sharpen,
            )

            result = ENHANCER.enhance_file(in_path, out_path, options)
            response_data = result.to_dict()
            response_data["original_url"] = f"/uploads/{in_filename}"
            response_data["download_url"] = f"/outputs/{out_filename}"
            self._send_json(response_data, status=HTTPStatus.OK)

        except Exception as exc:
            self._send_json(
                {"error": f"Failed to enhance image: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )


def run_web_app(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    open_browser: bool = True,
) -> None:
    """Start the local web application and optionally open the browser."""
    server = ThreadingHTTPServer((host, port), EnhancerHTTPRequestHandler)
    url = f"http://{host}:{port}"
    print("=" * 62)
    print(f"  ClearScale 1080p — Image Enhancer is running!")
    print(f"  Open in browser: {url}")
    print(f"  Press Ctrl+C to stop the application.")
    print("=" * 62)

    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down ClearScale 1080p Image Enhancer...")
        server.server_close()
