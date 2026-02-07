#!/usr/bin/env python3
"""Convert HEIC images to JPEG."""

import sys
from pathlib import Path
from pillow_heif import register_heif_opener
from PIL import Image

register_heif_opener()


def convert(input_path: str, quality: int = 95):
    src = Path(input_path)
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    dest = src.with_suffix(".jpg")
    img = Image.open(src)
    img.convert("RGB").save(dest, "JPEG", quality=quality)
    print(f"Saved: {dest}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_heic.py <file_or_folder>")
        print("  python convert_heic.py photo.heic")
        print("  python convert_heic.py input/Chaz/")
        sys.exit(1)

    target = Path(sys.argv[1])
    if target.is_dir():
        heics = list(target.glob("*.HEIC")) + list(target.glob("*.heic"))
        if not heics:
            print(f"No HEIC files found in {target}")
            sys.exit(1)
        for f in heics:
            convert(str(f))
        print(f"\nConverted {len(heics)} file(s)")
    else:
        convert(str(target))
