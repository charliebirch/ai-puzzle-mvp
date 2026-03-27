"""DEPRECATED — use quality.puzzle_scorer.score_puzzle_quality() instead.

This module's 5 metrics are fully subsumed by the 11-metric puzzle scorer:
  region_contrast → flat_region_pct + grid_uniformity
  detail_spread → grid_uniformity + corner_detail_ratio
  edge_contrast → edge_density + gradient_magnitude
  dead_zone_penalty → flat_region_pct (more precise)
  composition → subject_dominance

Kept temporarily for backward compatibility. Will be removed in a future cleanup.

Original description:
Puzzle-readiness assessment — checks whether an image will make a good jigsaw puzzle.
"""
import warnings
warnings.warn(
    "quality.puzzle_readiness is deprecated. Use quality.puzzle_scorer.score_puzzle_quality() instead.",
    DeprecationWarning,
    stacklevel=2,
)

import numpy as np
from PIL import Image
from typing import Dict, Tuple


def assess_puzzle_readiness(
    image_path: str,
    puzzle_pieces: int = 500,
) -> Dict:
    """Assess how well an image will work as a jigsaw puzzle.

    Args:
        image_path: Path to the image to assess.
        puzzle_pieces: Target puzzle piece count (500 or 1000).

    Returns:
        Dict with puzzle_readiness_score (0-100), pass/fail, and per-metric details.
    """
    img = Image.open(image_path).convert("RGB")
    img_array = np.array(img)

    # Determine grid — approximate piece layout
    # 500pc ≈ 20x25, 1000pc ≈ 25x40
    if puzzle_pieces >= 1000:
        grid_cols, grid_rows = 25, 40
    else:
        grid_cols, grid_rows = 20, 25

    # Compute per-region metrics
    region_contrasts = _region_contrast(img_array, grid_rows, grid_cols)
    detail_spread = _detail_spread_score(img_array, grid_rows, grid_cols)
    edge_contrast = _edge_contrast_score(img_array, grid_rows, grid_cols)
    dead_zone_pct = _dead_zone_percentage(region_contrasts)
    subject_coverage = _subject_coverage(img_array)

    # Weighted composite (0-100)
    # - Region contrast: are individual pieces distinguishable?
    # - Detail spread: is interest distributed across the whole image?
    # - Edge contrast: can you tell adjacent pieces apart?
    # - Dead zones penalty: large flat areas are bad
    # - Subject coverage: person shouldn't dominate the image (want <50%)
    weights = {
        "region_contrast": 0.25,
        "detail_spread": 0.25,
        "edge_contrast": 0.25,
        "dead_zone_penalty": 0.15,
        "composition": 0.10,
    }

    dead_zone_score = max(0, 100 - (dead_zone_pct * 3))  # 0% dead = 100, 33%+ dead = 0
    composition_score = _composition_score(subject_coverage)

    scores = {
        "region_contrast": min(100, region_contrasts["mean_contrast"] * 3.0),
        "detail_spread": detail_spread,
        "edge_contrast": edge_contrast,
        "dead_zone_penalty": dead_zone_score,
        "composition": composition_score,
    }

    composite = sum(scores[k] * weights[k] for k in weights)
    composite = round(min(100, max(0, composite)), 1)

    return {
        "puzzle_readiness_score": composite,
        "pass": composite >= 60,
        "grid": f"{grid_cols}x{grid_rows}",
        "metrics": {
            "region_contrast": {
                "score": round(scores["region_contrast"], 1),
                "mean_std": round(region_contrasts["mean_contrast"], 1),
                "min_std": round(region_contrasts["min_contrast"], 1),
                "description": "Average contrast within each piece region (higher = more detail per piece)",
            },
            "detail_spread": {
                "score": round(detail_spread, 1),
                "description": "How evenly visual detail is distributed across the image",
            },
            "edge_contrast": {
                "score": round(edge_contrast, 1),
                "description": "How distinguishable adjacent pieces are from each other",
            },
            "dead_zones": {
                "score": round(dead_zone_score, 1),
                "percentage": round(dead_zone_pct, 1),
                "description": f"{dead_zone_pct:.1f}% of piece regions are flat/uniform (low contrast)",
            },
            "composition": {
                "score": round(composition_score, 1),
                "subject_coverage_pct": round(subject_coverage * 100, 1),
                "description": "Whether the subject leaves room for scene detail (want <50% subject)",
            },
        },
    }


def _get_regions(img_array: np.ndarray, grid_rows: int, grid_cols: int):
    """Split image into grid regions, yielding (row, col, region_array)."""
    h, w = img_array.shape[:2]
    rh = h // grid_rows
    rw = w // grid_cols
    for r in range(grid_rows):
        for c in range(grid_cols):
            region = img_array[r * rh:(r + 1) * rh, c * rw:(c + 1) * rw]
            yield r, c, region


def _region_contrast(img_array: np.ndarray, grid_rows: int, grid_cols: int) -> Dict:
    """Compute contrast (std dev of luminance) for each piece region."""
    # Convert to grayscale
    gray = np.mean(img_array, axis=2)

    h, w = gray.shape
    rh = h // grid_rows
    rw = w // grid_cols

    stds = []
    for r in range(grid_rows):
        for c in range(grid_cols):
            region = gray[r * rh:(r + 1) * rh, c * rw:(c + 1) * rw]
            stds.append(np.std(region))

    stds = np.array(stds)
    return {
        "mean_contrast": float(np.mean(stds)),
        "min_contrast": float(np.min(stds)),
        "max_contrast": float(np.max(stds)),
        "std_contrast": float(np.std(stds)),
    }


def _detail_spread_score(img_array: np.ndarray, grid_rows: int, grid_cols: int) -> float:
    """Score how evenly visual detail is spread across the image.

    Uses entropy of the detail distribution — if all regions have similar detail,
    the distribution is uniform (high entropy = good). If detail is concentrated
    in one area, entropy is low (bad for puzzles).
    """
    gray = np.mean(img_array, axis=2)
    h, w = gray.shape
    rh = h // grid_rows
    rw = w // grid_cols

    # Compute detail (gradient magnitude) per region
    details = []
    for r in range(grid_rows):
        for c in range(grid_cols):
            region = gray[r * rh:(r + 1) * rh, c * rw:(c + 1) * rw]
            # Gradient magnitude as detail proxy
            gy = np.diff(region, axis=0)
            gx = np.diff(region, axis=1)
            grad_mag = np.mean(np.abs(gy[:-1, :])) + np.mean(np.abs(gx[:, :-1]))
            details.append(grad_mag)

    details = np.array(details)
    if details.sum() == 0:
        return 0.0

    # Normalize to probability distribution
    probs = details / details.sum()
    probs = probs[probs > 0]

    # Entropy — higher means more uniform spread
    entropy = -np.sum(probs * np.log2(probs))
    max_entropy = np.log2(len(details))  # uniform distribution

    if max_entropy == 0:
        return 0.0

    # Scale to 0-100
    return float((entropy / max_entropy) * 100)


def _edge_contrast_score(img_array: np.ndarray, grid_rows: int, grid_cols: int) -> float:
    """Score how distinguishable adjacent pieces are from each other.

    Compares mean color of neighboring regions — if neighbors look too similar,
    pieces will be hard to tell apart during assembly.
    """
    gray = np.mean(img_array, axis=2)
    h, w = gray.shape
    rh = h // grid_rows
    rw = w // grid_cols

    # Compute mean and std per region
    region_stats = {}
    for r in range(grid_rows):
        for c in range(grid_cols):
            region = gray[r * rh:(r + 1) * rh, c * rw:(c + 1) * rw]
            region_stats[(r, c)] = (float(np.mean(region)), float(np.std(region)))

    # Compare each region with its right and bottom neighbors
    diffs = []
    for r in range(grid_rows):
        for c in range(grid_cols):
            mean_a, std_a = region_stats[(r, c)]
            # Right neighbor
            if c + 1 < grid_cols:
                mean_b, std_b = region_stats[(r, c + 1)]
                diffs.append(abs(mean_a - mean_b) + abs(std_a - std_b))
            # Bottom neighbor
            if r + 1 < grid_rows:
                mean_b, std_b = region_stats[(r + 1, c)]
                diffs.append(abs(mean_a - mean_b) + abs(std_a - std_b))

    if not diffs:
        return 0.0

    # Average neighbor difference — scale to 0-100
    # A diff of ~20 is pretty good for puzzle distinguishability
    avg_diff = np.mean(diffs)
    return float(min(100, avg_diff * 4))


def _dead_zone_percentage(region_contrasts: Dict) -> float:
    """Percentage of regions with very low contrast (flat/uniform areas).

    These are the puzzle-killer — pieces from dead zones all look the same
    and are frustrating to assemble.
    """
    # A region with std < 8 is essentially flat (sky, solid color, etc.)
    threshold = 8.0
    mean_contrast = region_contrasts["mean_contrast"]
    # Approximate: if mean contrast is high, fewer dead zones
    # For a proper calculation we'd need all individual stds, but this approximates
    # by using the relationship between mean and min
    min_contrast = region_contrasts["min_contrast"]
    if min_contrast >= threshold:
        return 0.0  # Even the worst region has enough contrast

    # Estimate percentage based on how far below threshold the min is
    # relative to the mean
    if mean_contrast <= threshold:
        return 80.0  # Most of the image is flat

    ratio = (mean_contrast - threshold) / mean_contrast
    return float(max(0, (1 - ratio) * 50))


def _subject_coverage(img_array: np.ndarray) -> float:
    """Estimate what fraction of the image is dominated by a single subject.

    Uses center-weighted saliency as a proxy — if the center has much more
    detail than the edges, the subject is probably dominating the frame.
    """
    gray = np.mean(img_array, axis=2)
    h, w = gray.shape

    # Compare center third vs outer regions
    ch, cw = h // 3, w // 3
    center = gray[ch:2 * ch, cw:2 * cw]
    top = gray[:ch, :]
    bottom = gray[2 * ch:, :]
    left = gray[ch:2 * ch, :cw]
    right = gray[ch:2 * ch, 2 * cw:]

    center_detail = np.std(center)
    edge_details = [np.std(top), np.std(bottom), np.std(left), np.std(right)]
    edge_detail = np.mean(edge_details)

    if edge_detail == 0:
        return 1.0  # All detail in center

    # If center has much more detail than edges, subject is too dominant
    ratio = center_detail / (center_detail + edge_detail)
    # ratio of 0.5 = balanced, 0.7+ = center-heavy
    return float(min(1.0, max(0.0, (ratio - 0.3) / 0.4)))


def _composition_score(subject_coverage: float) -> float:
    """Score composition for puzzle suitability.

    Sweet spot is 20-45% subject coverage — enough to be recognizable,
    but leaves lots of scene for puzzle detail.
    """
    if subject_coverage < 0.2:
        return 70.0  # Person might be too small to recognize
    elif subject_coverage <= 0.45:
        return 100.0  # Sweet spot
    elif subject_coverage <= 0.6:
        return 70.0  # Getting portrait-heavy
    elif subject_coverage <= 0.8:
        return 40.0  # Too much subject
    else:
        return 20.0  # Basically a portrait — bad puzzle
