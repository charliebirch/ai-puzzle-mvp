"""
Export module for generating print-ready and preview files.

Handles bleed margins, DPI metadata, resolution validation, and color profiles.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw

from print_specs import get_bleed_px, get_print_profile, get_puzzle_spec


def add_bleed_margins(
    image: Image.Image,
    bleed_px: int,
    fill_color: Tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Add bleed margins around an image for print.

    Args:
        image: Source image.
        bleed_px: Bleed margin in pixels on each side.
        fill_color: Color to fill bleed area (default white).

    Returns:
        New image with bleed margins added.
    """
    w, h = image.size
    new_w = w + 2 * bleed_px
    new_h = h + 2 * bleed_px

    canvas = Image.new("RGB", (new_w, new_h), fill_color)
    canvas.paste(image, (bleed_px, bleed_px))
    return canvas


def set_dpi_metadata(image: Image.Image, dpi: int = 300) -> Image.Image:
    """Set DPI metadata on an image for print."""
    image.info["dpi"] = (dpi, dpi)
    return image


def add_grid_overlay(
    image: Image.Image,
    grid_cols: int,
    grid_rows: int,
    line_color: Tuple[int, int, int, int] = (0, 0, 0, 80),
    line_width: int = 2,
) -> Image.Image:
    """Add a puzzle grid overlay for preview images.

    Uses RGBA for semi-transparent lines.
    """
    img = image.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = img.size

    for i in range(1, grid_cols):
        x = i * (w // grid_cols)
        draw.line([(x, 0), (x, h)], fill=line_color, width=line_width)

    for i in range(1, grid_rows):
        y = i * (h // grid_rows)
        draw.line([(0, y), (w, y)], fill=line_color, width=line_width)

    result = Image.alpha_composite(img, overlay)
    return result.convert("RGB")


def export_preview(
    image_path: str,
    output_path: str,
    puzzle_pieces: int = 1000,
    max_preview_px: int = 1200,
) -> str:
    """Generate a preview image with puzzle grid overlay.

    Suitable for sending to customers for approval.
    """
    img = Image.open(image_path).convert("RGB")
    spec = get_puzzle_spec(puzzle_pieces)

    # Resize to preview size (not full print res)
    img.thumbnail((max_preview_px, max_preview_px), Image.LANCZOS)

    # Add grid overlay
    img = add_grid_overlay(img, spec["grid_cols"], spec["grid_rows"])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=90)
    return output_path


def export_print_ready(
    image_path: str,
    output_path: str,
    puzzle_pieces: int = 1000,
    supplier: str = "createjigsawpuzzles",
) -> Dict:
    """Generate a print-ready file with proper DPI, bleed, and resolution.

    Args:
        image_path: Path to the upscaled AI-generated image.
        output_path: Where to save the print-ready file.
        puzzle_pieces: Target puzzle piece count.
        supplier: Print supplier profile to use.

    Returns:
        Dict with export details and validation results.
    """
    img = Image.open(image_path).convert("RGB")
    spec = get_puzzle_spec(puzzle_pieces)
    profile = get_print_profile(supplier)
    bleed_px = get_bleed_px(supplier, profile["recommended_dpi"])

    target_w = spec["print_width_px"]
    target_h = spec["print_height_px"]

    # Resize to exact print dimensions if needed
    w, h = img.size
    if w != target_w or h != target_h:
        img = img.resize((target_w, target_h), Image.LANCZOS)

    # Add bleed margins
    img = add_bleed_margins(img, bleed_px)

    # Set DPI
    img = set_dpi_metadata(img, profile["recommended_dpi"])

    # Save with DPI metadata
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(
        output_path,
        quality=95,
        dpi=(profile["recommended_dpi"], profile["recommended_dpi"]),
    )

    final_w, final_h = img.size
    file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)

    return {
        "output_path": output_path,
        "dimensions": (final_w, final_h),
        "dimensions_without_bleed": (target_w, target_h),
        "bleed_px": bleed_px,
        "dpi": profile["recommended_dpi"],
        "file_size_mb": round(file_size_mb, 2),
        "meets_size_limit": file_size_mb <= profile["max_file_mb"],
        "puzzle_pieces": puzzle_pieces,
        "supplier": supplier,
    }
