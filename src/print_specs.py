"""
Print specifications for puzzle production.

Defines DPI, bleed, dimensions, and colorspace for print suppliers.
Primary supplier: createjigsawpuzzles.com
"""

from typing import Dict


# Print profiles per supplier
PRINT_PROFILES = {
    "createjigsawpuzzles": {
        "name": "Create Jigsaw Puzzles",
        "url": "https://www.createjigsawpuzzles.com",
        "min_dpi": 300,
        "recommended_dpi": 300,
        "bleed_inches": 0.125,
        "format": "JPEG",
        "colorspace": "sRGB",
        "max_file_mb": 50,
    },
}

# Puzzle size specs (dimensions in pixels at 300 DPI)
PUZZLE_SPECS = {
    500: {
        "pieces": 500,
        "label": "500-piece",
        "print_width_inches": 16,
        "print_height_inches": 20,
        "print_width_px": 4800,
        "print_height_px": 6000,
        "grid_cols": 20,
        "grid_rows": 25,
        "price_usd": 39.99,
    },
    1000: {
        "pieces": 1000,
        "label": "1000-piece",
        "print_width_inches": 20,
        "print_height_inches": 28,
        "print_width_px": 6000,
        "print_height_px": 8400,
        "grid_cols": 25,
        "grid_rows": 40,
        "price_usd": 49.99,
    },
}


def get_puzzle_spec(pieces: int) -> Dict:
    """Get the spec for a puzzle size.

    Args:
        pieces: Number of puzzle pieces (500 or 1000).

    Returns:
        Dict with puzzle dimensions and metadata.

    Raises:
        ValueError: If piece count is not supported.
    """
    if pieces not in PUZZLE_SPECS:
        available = ", ".join(str(k) for k in sorted(PUZZLE_SPECS.keys()))
        raise ValueError(f"Unsupported puzzle size {pieces}. Available: {available}")
    return PUZZLE_SPECS[pieces]


def get_print_profile(supplier: str = "createjigsawpuzzles") -> Dict:
    """Get print profile for a supplier."""
    if supplier not in PRINT_PROFILES:
        available = ", ".join(sorted(PRINT_PROFILES.keys()))
        raise ValueError(f"Unknown supplier '{supplier}'. Available: {available}")
    return PRINT_PROFILES[supplier]


def get_bleed_px(supplier: str = "createjigsawpuzzles", dpi: int = 300) -> int:
    """Calculate bleed margin in pixels."""
    profile = get_print_profile(supplier)
    return int(profile["bleed_inches"] * dpi)


def validate_print_ready(image_path: str, pieces: int = 1000) -> Dict:
    """Check if an image meets print requirements.

    Returns:
        Dict with validation results.
    """
    from PIL import Image

    img = Image.open(image_path)
    spec = get_puzzle_spec(pieces)
    w, h = img.size

    meets_width = w >= spec["print_width_px"]
    meets_height = h >= spec["print_height_px"]

    # Calculate effective DPI if we know print size
    effective_dpi_w = w / spec["print_width_inches"]
    effective_dpi_h = h / spec["print_height_inches"]

    return {
        "image_size": (w, h),
        "required_size": (spec["print_width_px"], spec["print_height_px"]),
        "meets_width": meets_width,
        "meets_height": meets_height,
        "meets_resolution": meets_width and meets_height,
        "effective_dpi": (round(effective_dpi_w), round(effective_dpi_h)),
        "min_dpi_met": min(effective_dpi_w, effective_dpi_h) >= 300,
    }
