"""
Automated image quality scoring for AI puzzle outputs.

Active metrics (tuned for animated/cartoon art):
- Color vibrancy (HSV saturation — rewards vivid cartoon colors)
- Edge cleanliness (Canny density — rewards clean cartoon edges, penalizes noise)
- Color diversity (histogram entropy)
- Resolution adequacy (vs target print size)

Legacy metrics (kept for diagnostics, not used in composite):
- Sharpness (Laplacian variance)
- Contrast (RMS)
"""

import math
from typing import Dict, Optional

import cv2
import numpy as np
from PIL import Image


def score_sharpness(image_path: str) -> float:
    """Score image sharpness using Laplacian variance.

    Returns:
        Sharpness score 0-100 (higher = sharper).
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0

    laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()

    # Map to 0-100 scale. Typical AI outputs: 50-500 variance.
    # Below 50 is blurry, above 300 is very sharp.
    score = min(100, max(0, (laplacian_var / 300) * 100))
    return round(score, 1)


def score_color_diversity(image_path: str) -> float:
    """Score color diversity using histogram entropy.

    Returns:
        Color diversity score 0-100.
    """
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)

    # Calculate histogram entropy for each channel
    entropies = []
    for c in range(3):
        hist, _ = np.histogram(arr[:, :, c].flatten(), bins=256, range=(0, 256))
        hist = hist / hist.sum()
        hist = hist[hist > 0]
        entropy = -np.sum(hist * np.log2(hist))
        entropies.append(entropy)

    avg_entropy = np.mean(entropies)
    # Max entropy for 256 bins is 8.0, typical images: 5-7.5
    score = min(100, max(0, (avg_entropy / 7.5) * 100))
    return round(score, 1)


def score_contrast(image_path: str) -> float:
    """Score image contrast using RMS contrast.

    Returns:
        Contrast score 0-100.
    """
    img = Image.open(image_path).convert("L")
    arr = np.array(img, dtype=np.float64)
    rms = np.sqrt(np.mean((arr - arr.mean()) ** 2))

    # RMS contrast range: 0-128. Typical good images: 40-80.
    score = min(100, max(0, (rms / 70) * 100))
    return round(score, 1)


def score_resolution(image_path: str, target_pieces: int = 1000) -> float:
    """Score resolution adequacy relative to puzzle print requirements.

    Returns:
        Resolution score 0-100 (100 = meets or exceeds target).
    """
    from print_specs import get_puzzle_spec

    img = Image.open(image_path)
    w, h = img.size
    spec = get_puzzle_spec(target_pieces)

    target_w = spec["print_width_px"]
    target_h = spec["print_height_px"]

    # Score based on how close we are to target dimensions
    ratio_w = w / target_w
    ratio_h = h / target_h
    ratio = min(ratio_w, ratio_h)

    if ratio >= 1.0:
        return 100.0
    return round(ratio * 100, 1)


def score_color_vibrancy(image_path: str) -> float:
    """Score color vibrancy using mean HSV saturation.

    Cartoon/animated art has vivid, saturated colors. This rewards that.

    Returns:
        Vibrancy score 0-100 (higher = more saturated/vivid).
    """
    img = cv2.imread(image_path)
    if img is None:
        return 0.0

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mean_sat = np.mean(hsv[:, :, 1])  # S channel 0-255
    high_sat_ratio = np.mean(hsv[:, :, 1] > 80) * 100  # % of pixels with S > 80

    # Blend: 60% normalized mean saturation + 40% high-saturation pixel ratio
    score = (mean_sat / 160 * 100) * 0.6 + high_sat_ratio * 0.4
    return round(min(100, max(0, score)), 1)


def score_edge_cleanliness(image_path: str) -> float:
    """Score edge cleanliness using Canny edge density.

    Clean cartoon art has sparse, deliberate edges (5-18% density).
    Photorealistic textures or artifacts produce dense noisy edges (>18%).
    Featureless blobs have too few edges (<3%).

    Returns:
        Edge cleanliness score 0-100.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0

    edges = cv2.Canny(img, 50, 150)
    edge_density = np.mean(edges > 0) * 100  # percentage of edge pixels

    # Sweet spot: 5-18% density = 100
    if 5 <= edge_density <= 18:
        score = 100.0
    elif edge_density < 3:
        # Too few edges — featureless
        score = (edge_density / 3) * 60
    elif edge_density < 5:
        # Slightly below sweet spot
        score = 60 + (edge_density - 3) / 2 * 40
    else:
        # Above 18% — noisy/photorealistic, penalize
        score = max(0, 100 - (edge_density - 18) * 5)

    return round(min(100, max(0, score)), 1)


def assess_image_quality(
    image_path: str,
    target_pieces: int = 1000,
) -> Dict:
    """Full quality assessment of an image.

    Returns dict with active metrics for composite scoring,
    plus legacy metrics for diagnostics.
    """
    # Active metrics (used in composite)
    color_vibrancy = score_color_vibrancy(image_path)
    edge_cleanliness = score_edge_cleanliness(image_path)
    color_diversity = score_color_diversity(image_path)
    resolution = score_resolution(image_path, target_pieces)

    # Legacy metrics (diagnostics only, not in composite)
    sharpness = score_sharpness(image_path)
    contrast = score_contrast(image_path)

    scores = {
        "color_vibrancy": color_vibrancy,
        "edge_cleanliness": edge_cleanliness,
        "color_diversity": color_diversity,
        "resolution": resolution,
        # Legacy (diagnostics)
        "sharpness_legacy": sharpness,
        "contrast_legacy": contrast,
    }

    return scores


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Score image quality.")
    parser.add_argument("image", help="Image to score")
    parser.add_argument("--pieces", type=int, default=1000, help="Target puzzle pieces")
    args = parser.parse_args()

    scores = assess_image_quality(args.image, args.pieces)
    print(f"Quality scores for {args.image}:")
    for k, v in scores.items():
        print(f"  {k}: {v}/100")
