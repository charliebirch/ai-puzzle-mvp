"""
Image upscaling via Real-ESRGAN on Replicate.

Upscales AI-generated images to print-ready resolution.
Cost: ~$0.002/run on Replicate.
"""

import os
from io import BytesIO
from pathlib import Path
from typing import Optional

import replicate
import requests
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

REPLICATE_MODEL = "nightmareai/real-esrgan:b3ef194191d13140337468c916c2c5b96dd0cb06dffc032a022a31807f6a5ea8"
COST_PER_RUN = 0.002


def _extract_url(output) -> str:
    """Extract URL from Replicate output."""
    if isinstance(output, list):
        output = output[0]
    if isinstance(output, str):
        return output
    if hasattr(output, "url"):
        url_attr = getattr(output, "url")
        return url_attr() if callable(url_attr) else url_attr
    return str(output)


def upscale_image(
    input_path: str,
    output_path: str,
    scale: int = 4,
    face_enhance: bool = True,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
) -> dict:
    """Upscale an image using Real-ESRGAN.

    Args:
        input_path: Path to the input image.
        output_path: Where to save the upscaled image.
        scale: Upscale factor (2 or 4).
        face_enhance: Enable face region enhancement (GFPGAN).
        target_width: Optional target width for final resize.
        target_height: Optional target height for final resize.

    Returns:
        Dict with output info (path, size, cost).
    """
    print(f"Upscaling {input_path} ({scale}x, face_enhance={face_enhance})...")

    inputs = {
        "image": open(input_path, "rb"),
        "scale": scale,
        "face_enhance": face_enhance,
    }

    output = replicate.run(REPLICATE_MODEL, input=inputs)
    image_url = _extract_url(output)

    response = requests.get(image_url, timeout=120)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content))

    upscaled_size = img.size
    print(f"  Upscaled to {img.size[0]}x{img.size[1]}")

    # Resize to exact target dimensions if specified
    if target_width and target_height:
        img = img.resize((target_width, target_height), Image.LANCZOS)
        print(f"  Resized to {target_width}x{target_height}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)
    print(f"  Saved to {output_path}")

    return {
        "input_path": input_path,
        "output_path": output_path,
        "upscaled_size": upscaled_size,
        "final_size": img.size,
        "scale": scale,
        "face_enhance": face_enhance,
        "cost_estimate": COST_PER_RUN,
    }


def upscale_for_print(
    input_path: str,
    output_path: str,
    puzzle_pieces: int = 1000,
    dpi: int = 300,
) -> dict:
    """Upscale an image to meet print requirements for a specific puzzle size.

    Args:
        input_path: Path to the AI-generated image.
        output_path: Where to save the print-ready image.
        puzzle_pieces: Target puzzle piece count (500 or 1000).
        dpi: Target DPI for printing.

    Returns:
        Dict with output info.
    """
    from print_specs import get_puzzle_spec

    spec = get_puzzle_spec(puzzle_pieces)
    target_w = spec["print_width_px"]
    target_h = spec["print_height_px"]

    # Determine upscale factor needed
    img = Image.open(input_path)
    current_max = max(img.size)
    target_max = max(target_w, target_h)

    # Use 2x to avoid GPU OOM on Replicate (4x on 1280px+ images exceeds 14GB VRAM).
    # The final Lanczos resize to target dimensions handles the rest cleanly.
    scale = 2

    return upscale_image(
        input_path=input_path,
        output_path=output_path,
        scale=scale,
        face_enhance=True,
        target_width=target_w,
        target_height=target_h,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Upscale images for print.")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("--output", default=None, help="Output path (default: input_upscaled.png)")
    parser.add_argument("--scale", type=int, default=4, choices=[2, 4])
    parser.add_argument("--face-enhance", action="store_true", default=True)
    parser.add_argument("--puzzle-pieces", type=int, default=None, choices=[500, 1000],
                        help="Target puzzle size (auto-sets dimensions)")
    args = parser.parse_args()

    output = args.output or str(Path(args.input).stem) + "_upscaled.png"

    if args.puzzle_pieces:
        upscale_for_print(args.input, output, args.puzzle_pieces)
    else:
        upscale_image(args.input, output, args.scale, args.face_enhance)
