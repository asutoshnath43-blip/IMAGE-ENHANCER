#!/usr/bin/env python3
"""
Universal Start File for ClearScale 1080p Image Enhancer.
Double-click or run `python start.py` to verify dependencies and open the application.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
os.chdir(ROOT_DIR)


def check_dependencies() -> bool:
    """Verify that Pillow and numpy are available; offer automatic pip install if missing."""
    missing = []
    for mod, pkg in [("PIL", "Pillow"), ("numpy", "numpy")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)

    if not missing:
        return True

    print(f"[Setup] Installing required packages: {', '.join(missing)}...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", str(ROOT_DIR / "requirements.txt")]
        )
        return True
    except Exception as exc:
        print(f"[Error] Could not install dependencies automatically: {exc}")
        print("Please run: pip install -r requirements.txt")
        return False


def start() -> None:
    if not check_dependencies():
        sys.exit(1)

    from main import main
    sys.exit(main())


if __name__ == "__main__":
    start()
