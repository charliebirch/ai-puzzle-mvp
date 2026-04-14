"""Teeth whitening post-processor for cartoon character headshots.

Targets the mouth region of a head-and-shoulders portrait and shifts
tooth-coloured pixels (light, yellowish) toward clean white. Works on
Pixar-style cartoon outputs where teeth are a small, well-defined area.

Runs purely in PIL/NumPy — no API cost, deterministic, <100ms.
"""

from pathlib import Path

import numpy as np
from PIL import Image


# --- Tuning constants ---

# Vertical band of the image to search for teeth (head-and-shoulders portrait).
# Mouth sits in the lower-middle portion of a centred face.
MOUTH_Y_START = 0.52  # fraction from top
MOUTH_Y_END = 0.72
# Horizontal band — mouth is centrally located
MOUTH_X_START = 0.30
MOUTH_X_END = 0.70

# HSV thresholds for "tooth-like" pixels (PIL HSV: H 0-255, S 0-255, V 0-255).
# Teeth are very bright, nearly desaturated, and slightly warm/yellow.
# Must exclude: white background (V>0.95, S~0), skin (higher saturation).
MIN_LIGHTNESS = 0.68   # brighter than skin
MAX_LIGHTNESS = 0.95   # exclude pure white background
MAX_SATURATION = 0.22  # teeth are nearly grey — skin is warmer/more saturated
# Hue range for yellow/warm tones (PIL HSV: 0-255 maps to 0-360 degrees)
# Yellow sits around 30-70 degrees → ~21-50 in 0-255 space
HUE_YELLOW_LOW = 10
HUE_YELLOW_HIGH = 55

# How aggressively to whiten (0.0 = no change, 1.0 = full replacement)
WHITEN_STRENGTH = 0.7
# Target colour for whitened teeth (slightly warm white, not blue-white)
TARGET_RGB = np.array([252, 250, 245], dtype=np.float64)


def whiten_teeth(image_path: str, output_path: str = None) -> str:
    """Whiten teeth in a cartoon headshot image.

    Detects tooth-coloured pixels in the mouth region and shifts them
    toward clean white. Safe on images with no visible teeth — if no
    tooth pixels are found, the image is saved unchanged.

    Args:
        image_path: Path to the input headshot PNG/JPG.
        output_path: Where to save the result. Defaults to overwriting
            the input file.

    Returns:
        Path to the output image.
    """
    if output_path is None:
        output_path = image_path

    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img, dtype=np.float64)
    h, w, _ = pixels.shape

    # Define the mouth search region
    y0 = int(h * MOUTH_Y_START)
    y1 = int(h * MOUTH_Y_END)
    x0 = int(w * MOUTH_X_START)
    x1 = int(w * MOUTH_X_END)

    # Work on the mouth region only
    region = pixels[y0:y1, x0:x1].copy()

    # Convert to HSV for thresholding
    region_img = Image.fromarray(region.astype(np.uint8))
    hsv = np.array(region_img.convert("HSV"), dtype=np.float64)

    hue = hsv[:, :, 0]        # 0-255 (maps to 0-360 degrees)
    sat = hsv[:, :, 1] / 255  # normalise to 0-1
    val = hsv[:, :, 2] / 255  # normalise to 0-1

    # Build tooth mask: bright (but not background-white), low saturation, yellow-ish hue
    tooth_mask = (
        (val >= MIN_LIGHTNESS)
        & (val <= MAX_LIGHTNESS)
        & (sat <= MAX_SATURATION)
        & (hue >= HUE_YELLOW_LOW)
        & (hue <= HUE_YELLOW_HIGH)
    )

    n_tooth_pixels = tooth_mask.sum()
    region_pixels = region.shape[0] * region.shape[1]

    # Safety: if teeth are more than 15% of the mouth region, something
    # is wrong (probably matched skin or background). Skip whitening.
    if n_tooth_pixels > region_pixels * 0.15:
        print(f"  teeth_whitening: skipped — {n_tooth_pixels} tooth pixels "
              f"({n_tooth_pixels / region_pixels:.1%} of mouth region) exceeds safety limit")
        img.save(output_path, quality=95)
        return output_path

    if n_tooth_pixels == 0:
        print("  teeth_whitening: no tooth pixels detected, image unchanged")
        img.save(output_path, quality=95)
        return output_path

    # Blend tooth pixels toward target white
    for c in range(3):
        channel = region[:, :, c]
        channel[tooth_mask] = (
            channel[tooth_mask] * (1 - WHITEN_STRENGTH)
            + TARGET_RGB[c] * WHITEN_STRENGTH
        )

    # Write the whitened region back
    pixels[y0:y1, x0:x1] = region
    result = Image.fromarray(pixels.astype(np.uint8))
    result.save(output_path, quality=95)

    print(f"  teeth_whitening: whitened {n_tooth_pixels} pixels "
          f"in mouth region ({n_tooth_pixels / region_pixels:.1%})")
    return output_path
