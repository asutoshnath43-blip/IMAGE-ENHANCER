"""
Native Desktop GUI (Tkinter) for ClearScale 1080p Image Enhancer.
Provides a minimalistic native window to upload/select an image, enhance to 1080p,
preview, and save/download the enhanced image.
"""
import shutil
from pathlib import Path
from typing import Optional

from PIL import Image, ImageTk

from config import APP_NAME, UPLOAD_DIR, OUTPUT_DIR
from enhancer import ImageEnhancer1080p, EnhancementOptions


def run_desktop_app() -> None:
    """Launch the minimalistic native Tkinter desktop interface."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError as exc:
        raise RuntimeError(
            "Tkinter is not installed in this Python environment. "
            "Run `python start.py` (default web UI mode) instead."
        ) from exc

    enhancer = ImageEnhancer1080p()
    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("920x600")
    root.configure(bg="#f8fafc")

    state = {
        "input_path": None,
        "output_path": None,
        "preview_photo": None,
    }

    header = tk.Frame(root, bg="#ffffff", pady=14, padx=20)
    header.pack(fill="x")
    tk.Label(
        header,
        text="ClearScale 1080p — Image Enhancer",
        font=("Segoe UI", 14, "bold"),
        bg="#ffffff",
        fg="#0f172a",
    ).pack(side="left")

    body = tk.Frame(root, bg="#f8fafc", padx=20, pady=16)
    body.pack(fill="both", expand=True)

    controls = tk.Frame(body, bg="#ffffff", padx=18, pady=18, width=280)
    controls.pack(side="left", fill="y", padx=(0, 16))

    preview_frame = tk.Frame(body, bg="#ffffff", padx=16, pady=16)
    preview_frame.pack(side="right", fill="both", expand=True)

    status_var = tk.StringVar(value="Upload an image to enhance to 1080p HD.")
    preset_var = tk.StringVar(value="balanced")
    scaling_var = tk.StringVar(value="fit_1080p")

    preview_label = tk.Label(
        preview_frame,
        text="No image loaded",
        bg="#f1f5f9",
        fg="#64748b",
        font=("Segoe UI", 11),
    )
    preview_label.pack(fill="both", expand=True)

    def show_image_on_canvas(img_path: Path) -> None:
        with Image.open(img_path) as im:
            im.thumbnail((560, 440), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(im)
            state["preview_photo"] = photo
            preview_label.configure(image=photo, text="")

    def select_image() -> None:
        file_path = filedialog.askopenfilename(
            title="Select Low-Resolution Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff")],
        )
        if not file_path:
            return
        in_p = Path(file_path)
        state["input_path"] = in_p
        show_image_on_canvas(in_p)
        with Image.open(in_p) as im:
            w, h = im.size
        status_var.set(f"Loaded: {in_p.name} ({w}x{h} px). Ready to enhance.")
        enhance_btn.configure(state="normal")

    def enhance_image() -> None:
        in_p: Optional[Path] = state["input_path"]
        if not in_p:
            return
        status_var.set("Enhancing to 1080p HD...")
        root.update_idletasks()
        out_p = OUTPUT_DIR / f"{in_p.stem}_1080p.png"
        opts = EnhancementOptions(
            preset=preset_var.get(),
            scaling_mode=scaling_var.get(),
            output_format="PNG",
        )
        res = enhancer.enhance_file(in_p, out_p, opts)
        state["output_path"] = out_p
        show_image_on_canvas(out_p)
        status_var.set(
            f"Enhanced: {res.enhanced_width}x{res.enhanced_height} px "
            f"({res.scale_factor}x) in {res.processing_time_ms} ms"
        )
        download_btn.configure(state="normal")

    def download_image() -> None:
        out_p: Optional[Path] = state["output_path"]
        if not out_p or not out_p.exists():
            return
        save_to = filedialog.asksaveasfilename(
            title="Save Enhanced 1080p Image",
            defaultextension=".png",
            initialfile=out_p.name,
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")],
        )
        if save_to:
            shutil.copyfile(out_p, save_to)
            messagebox.showinfo("Saved", f"Enhanced 1080p image saved to:\n{save_to}")

    tk.Button(
        controls,
        text="1. Upload Image",
        command=select_image,
        bg="#2563eb",
        fg="#ffffff",
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        pady=8,
    ).pack(fill="x", pady=(0, 14))

    tk.Label(controls, text="Enhancement Preset:", bg="#ffffff", anchor="w").pack(fill="x")
    ttk.Combobox(
        controls,
        textvariable=preset_var,
        values=["balanced", "crisp", "photo_restore", "illustration"],
        state="readonly",
    ).pack(fill="x", pady=(4, 12))

    tk.Label(controls, text="1080p Framing:", bg="#ffffff", anchor="w").pack(fill="x")
    ttk.Combobox(
        controls,
        textvariable=scaling_var,
        values=["fit_1080p", "exact_1920x1080_pad", "exact_1920x1080_crop"],
        state="readonly",
    ).pack(fill="x", pady=(4, 16))

    enhance_btn = tk.Button(
        controls,
        text="2. Enhance to 1080p",
        command=enhance_image,
        bg="#0f172a",
        fg="#ffffff",
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        pady=8,
        state="disabled",
    )
    enhance_btn.pack(fill="x", pady=(0, 10))

    download_btn = tk.Button(
        controls,
        text="3. Download / Save 1080p",
        command=download_image,
        bg="#059669",
        fg="#ffffff",
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        pady=8,
        state="disabled",
    )
    download_btn.pack(fill="x", pady=(0, 16))

    tk.Label(
        controls,
        textvariable=status_var,
        bg="#f1f5f9",
        fg="#334155",
        wraplength=230,
        justify="left",
        padx=8,
        pady=8,
    ).pack(fill="x", side="bottom")

    root.mainloop()
