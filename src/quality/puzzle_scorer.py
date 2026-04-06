"""Unified puzzle quality scoring — 12 metrics that predict physical puzzle solvability.

Implements metrics from the deep research document (docs/complete-ai-puzzle-guide-deep-research.md).
All computed on image resized to 1500px long edge. Only uses numpy + opencv (no torch, no InsightFace).
Target: <2s total scoring time.

Scoring grades:
    >= 65: PASS
    40-64: WARNING (manual review)
    < 40:  FAIL
    Any hard fail: HARD_FAIL regardless of score
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


class PuzzleGrade(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    HARD_FAIL = "HARD_FAIL"


@dataclass
class MetricResult:
    """Result for a single metric."""
    name: str
    raw_value: float
    normalized_score: float  # 0-100
    weight: float
    hard_fail: bool = False
    hard_fail_reason: str = ""


@dataclass
class PuzzleScore:
    """Complete puzzle quality score."""
    composite: float
    grade: PuzzleGrade
    per_metric: Dict[str, MetricResult] = field(default_factory=dict)
    hard_fail_reasons: List[str] = field(default_factory=list)
    transformation_score: Optional[float] = None  # 0-100, None if no source provided


# Metric weights — quality metrics sum to 1.0.
# white_patch is weight 0 — pure hard fail detector, no composite score contribution.
METRIC_WEIGHTS = {
    "flat_region_pct": 0.20,
    "color_entropy": 0.12,
    "edge_density": 0.12,
    "corner_detail_ratio": 0.12,
    "grid_uniformity": 0.10,
    "dominant_color_pct": 0.08,
    "gradient_magnitude": 0.06,
    "hue_diversity": 0.06,
    "laplacian_variance": 0.06,
    "gabor_texture_energy": 0.04,
    "subject_dominance": 0.04,
    "white_patch": 0.00,  # hard fail only — failed composite detector
}

# Analysis resolution — all images resized to this long edge before scoring
ANALYSIS_LONG_EDGE = 1500


def _resize_for_analysis(img: np.ndarray) -> np.ndarray:
    """Resize image so long edge is ANALYSIS_LONG_EDGE pixels."""
    h, w = img.shape[:2]
    long_edge = max(h, w)
    if long_edge <= ANALYSIS_LONG_EDGE:
        return img
    scale = ANALYSIS_LONG_EDGE / long_edge
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _score_flat_region_pct(gray: np.ndarray, piece_window: int = 64) -> MetricResult:
    """Metric 1: Percentage of image that is flat (low local variance).

    Uses blur-based local variance with piece-sized window (~64px).
    Flat regions make pieces indistinguishable.

    Pass: <25%, Fail: >40%, Hard fail: >50%
    """
    # Compute local variance using blur trick: var = E[X^2] - E[X]^2
    gray_f = gray.astype(np.float64)
    mean = cv2.blur(gray_f, (piece_window, piece_window))
    mean_sq = cv2.blur(gray_f ** 2, (piece_window, piece_window))
    local_var = mean_sq - mean ** 2

    # Threshold: variance < 100 means flat
    flat_mask = local_var < 100
    flat_pct = np.mean(flat_mask) * 100

    # Normalize to 0-100 score (lower flat_pct = better)
    if flat_pct <= 25:
        score = 100.0
    elif flat_pct <= 40:
        score = 100 - (flat_pct - 25) / 15 * 60  # 100 → 40
    elif flat_pct <= 50:
        score = 40 - (flat_pct - 40) / 10 * 30   # 40 → 10
    else:
        score = max(0, 10 - (flat_pct - 50) / 10 * 10)

    hard_fail = flat_pct > 50
    return MetricResult(
        name="flat_region_pct",
        raw_value=round(flat_pct, 1),
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["flat_region_pct"],
        hard_fail=hard_fail,
        hard_fail_reason=f"Flat regions cover {flat_pct:.0f}% of image (>50% hard fail)" if hard_fail else "",
    )


def _score_color_entropy(img_bgr: np.ndarray) -> MetricResult:
    """Metric 2: Shannon entropy on per-channel 256-bin histograms.

    Higher entropy = more diverse color distribution.
    Pass: >6.5 bits, Fail: <5.5 bits
    """
    entropies = []
    for c in range(3):
        hist, _ = np.histogram(img_bgr[:, :, c].flatten(), bins=256, range=(0, 256))
        hist = hist / hist.sum()
        hist = hist[hist > 0]
        entropy = -np.sum(hist * np.log2(hist))
        entropies.append(entropy)

    avg_entropy = float(np.mean(entropies))

    # Normalize: 5.5 → 0, 6.5 → 70, 7.5 → 100
    if avg_entropy >= 7.5:
        score = 100.0
    elif avg_entropy >= 6.5:
        score = 70 + (avg_entropy - 6.5) / 1.0 * 30
    elif avg_entropy >= 5.5:
        score = (avg_entropy - 5.5) / 1.0 * 70
    else:
        score = max(0, avg_entropy / 5.5 * 30)

    return MetricResult(
        name="color_entropy",
        raw_value=round(avg_entropy, 2),
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["color_entropy"],
    )


def _score_edge_density(gray: np.ndarray) -> MetricResult:
    """Metric 3: Canny edge density with auto-threshold.

    Pass: >8%, Fail: <4%, Hard fail: <1%
    Original hard fail was <2% — loosened to <1% because cartoon art with smooth
    shading naturally has lower edge density than photographs.
    (Original thresholds: pass >8%, fail <4%, hard_fail <2%)
    """
    # Median-based auto-threshold (Otsu alternative)
    median_val = np.median(gray)
    low = int(max(0, 0.67 * median_val))
    high = int(min(255, 1.33 * median_val))
    edges = cv2.Canny(gray, low, high)
    density = np.mean(edges > 0) * 100

    if density >= 8:
        score = 100.0
    elif density >= 4:
        score = 40 + (density - 4) / 4 * 60
    elif density >= 1:
        score = (density - 1) / 3 * 40
    else:
        score = 0.0

    hard_fail = density < 1
    return MetricResult(
        name="edge_density",
        raw_value=round(density, 2),
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["edge_density"],
        hard_fail=hard_fail,
        hard_fail_reason=f"Edge density only {density:.1f}% (<1% hard fail)" if hard_fail else "",
    )


def _score_corner_detail_ratio(gray: np.ndarray) -> MetricResult:
    """Metric 4: Laplacian variance in 4 corners vs center.

    Corners need detail for puzzle assembly (edge pieces first).
    Pass: min corner ratio >0.15, Fail: <0.10, Hard fail: any <0.02
    Original hard fail was <0.05 — loosened to <0.02 because cartoon scenes
    often have stylized sky/ground corners with less detail than the center.
    (Original thresholds: pass >0.15, fail <0.10, hard_fail <0.05)
    """
    h, w = gray.shape
    corner_h = int(h * 0.20)
    corner_w = int(w * 0.20)
    center_h = int(h * 0.50)
    center_w = int(w * 0.50)

    # Center region
    ch_start = (h - center_h) // 2
    cw_start = (w - center_w) // 2
    center = gray[ch_start:ch_start + center_h, cw_start:cw_start + center_w]
    center_var = cv2.Laplacian(center, cv2.CV_64F).var()

    if center_var == 0:
        center_var = 0.001  # avoid division by zero

    # Four corners
    corners = [
        gray[:corner_h, :corner_w],                    # top-left
        gray[:corner_h, w - corner_w:],                # top-right
        gray[h - corner_h:, :corner_w],                # bottom-left
        gray[h - corner_h:, w - corner_w:],            # bottom-right
    ]
    corner_ratios = []
    for corner in corners:
        corner_var = cv2.Laplacian(corner, cv2.CV_64F).var()
        corner_ratios.append(corner_var / center_var)

    min_ratio = min(corner_ratios)

    # Normalize
    if min_ratio >= 0.15:
        score = 100.0
    elif min_ratio >= 0.10:
        score = 40 + (min_ratio - 0.10) / 0.05 * 60
    elif min_ratio >= 0.02:
        score = (min_ratio - 0.02) / 0.08 * 40
    else:
        score = 0.0

    hard_fail = any(r < 0.02 for r in corner_ratios)
    return MetricResult(
        name="corner_detail_ratio",
        raw_value=round(min_ratio, 3),
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["corner_detail_ratio"],
        hard_fail=hard_fail,
        hard_fail_reason=f"Corner detail ratio {min_ratio:.3f} (<0.02 hard fail)" if hard_fail else "",
    )


def _score_grid_uniformity(gray: np.ndarray) -> MetricResult:
    """Metric 5: Coefficient of variation of entropy across 4x4 grid.

    Measures how evenly detail is distributed. Low CV = uniform = good.
    Pass: CV <0.35, Fail: CV >0.55
    Also checks: each cell must have >40% of mean entropy.
    """
    h, w = gray.shape
    grid_rows, grid_cols = 4, 4
    rh = h // grid_rows
    rw = w // grid_cols

    cell_entropies = []
    for r in range(grid_rows):
        for c in range(grid_cols):
            cell = gray[r * rh:(r + 1) * rh, c * rw:(c + 1) * rw]
            hist, _ = np.histogram(cell.flatten(), bins=256, range=(0, 256))
            hist = hist / hist.sum()
            hist = hist[hist > 0]
            entropy = -np.sum(hist * np.log2(hist))
            cell_entropies.append(entropy)

    cell_entropies = np.array(cell_entropies)
    mean_ent = np.mean(cell_entropies)
    std_ent = np.std(cell_entropies)
    cv = std_ent / mean_ent if mean_ent > 0 else 1.0

    # Check minimum cell threshold
    min_cell_ratio = np.min(cell_entropies) / mean_ent if mean_ent > 0 else 0

    if cv <= 0.35 and min_cell_ratio >= 0.40:
        score = 100.0
    elif cv <= 0.55:
        score = 100 - (cv - 0.35) / 0.20 * 60
        if min_cell_ratio < 0.40:
            score *= 0.7  # penalty for dead cells
    else:
        score = max(0, 40 - (cv - 0.55) / 0.20 * 40)

    return MetricResult(
        name="grid_uniformity",
        raw_value=round(cv, 3),
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["grid_uniformity"],
    )


def _score_dominant_color_pct(img_bgr: np.ndarray) -> MetricResult:
    """Metric 6: Largest color cluster percentage using k-means.

    k=5 on 10K sampled pixels from 500px downsample.
    Pass: <35%, Fail: >50%, Hard fail: >60%
    """
    # Downsample to 500px for k-means
    h, w = img_bgr.shape[:2]
    scale = 500 / max(h, w)
    if scale < 1:
        small = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    else:
        small = img_bgr

    # Sample 10K pixels
    pixels = small.reshape(-1, 3).astype(np.float32)
    n_pixels = len(pixels)
    if n_pixels > 10000:
        indices = np.random.choice(n_pixels, 10000, replace=False)
        pixels = pixels[indices]

    # k-means with k=5
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, _ = cv2.kmeans(pixels, 5, None, criteria, 3, cv2.KMEANS_PP_CENTERS)

    # Find dominant cluster percentage
    unique, counts = np.unique(labels, return_counts=True)
    dominant_pct = float(np.max(counts) / np.sum(counts) * 100)

    if dominant_pct <= 35:
        score = 100.0
    elif dominant_pct <= 50:
        score = 100 - (dominant_pct - 35) / 15 * 60
    elif dominant_pct <= 60:
        score = 40 - (dominant_pct - 50) / 10 * 30
    else:
        score = max(0, 10 - (dominant_pct - 60) / 10 * 10)

    hard_fail = dominant_pct > 60
    return MetricResult(
        name="dominant_color_pct",
        raw_value=round(dominant_pct, 1),
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["dominant_color_pct"],
        hard_fail=hard_fail,
        hard_fail_reason=f"Single color covers {dominant_pct:.0f}% of image (>60% hard fail)" if hard_fail else "",
    )


def _score_gradient_magnitude(gray: np.ndarray) -> MetricResult:
    """Metric 7: Mean Sobel gradient magnitude.

    Higher = more texture/detail transitions.
    Pass: mean >15, Fail: mean <10
    """
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
    mean_grad = float(np.mean(magnitude))

    if mean_grad >= 15:
        score = 100.0
    elif mean_grad >= 10:
        score = 40 + (mean_grad - 10) / 5 * 60
    else:
        score = max(0, mean_grad / 10 * 40)

    return MetricResult(
        name="gradient_magnitude",
        raw_value=round(mean_grad, 1),
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["gradient_magnitude"],
    )


def _score_hue_diversity(img_bgr: np.ndarray) -> MetricResult:
    """Metric 8: Number of occupied hue bins.

    HSV hue in 18 bins (10 degrees each), excluding low-saturation pixels (S<30).
    Pass: >=8 bins, Fail: <5 bins
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    # Filter out low-saturation pixels
    mask = hsv[:, :, 1] >= 30
    hue_values = hsv[:, :, 0][mask]  # OpenCV hue is 0-179

    if len(hue_values) == 0:
        return MetricResult(
            name="hue_diversity",
            raw_value=0,
            normalized_score=0.0,
            weight=METRIC_WEIGHTS["hue_diversity"],
        )

    # 18 bins of 10 degrees each (OpenCV hue 0-179 → 18 bins)
    hist, _ = np.histogram(hue_values, bins=18, range=(0, 180))
    total_pixels = np.sum(hist)

    # Count bins with >0.5% of pixels
    threshold = total_pixels * 0.005
    occupied_bins = int(np.sum(hist > threshold))

    if occupied_bins >= 8:
        score = 100.0
    elif occupied_bins >= 5:
        score = 30 + (occupied_bins - 5) / 3 * 70
    else:
        score = max(0, occupied_bins / 5 * 30)

    return MetricResult(
        name="hue_diversity",
        raw_value=occupied_bins,
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["hue_diversity"],
    )


def _score_laplacian_variance(gray: np.ndarray) -> MetricResult:
    """Metric 9: Global Laplacian variance (sharpness).

    Pass: >500, Fail: <200
    """
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    if lap_var >= 500:
        score = 100.0
    elif lap_var >= 200:
        score = 30 + (lap_var - 200) / 300 * 70
    else:
        score = max(0, lap_var / 200 * 30)

    return MetricResult(
        name="laplacian_variance",
        raw_value=round(lap_var, 1),
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["laplacian_variance"],
    )


def _score_gabor_texture_energy(gray: np.ndarray) -> MetricResult:
    """Metric 10: Gabor filter bank response (texture richness).

    4 frequencies x 4 orientations, mean energy across all.
    Pass: >10, Fail: <5
    """
    energies = []
    for freq in [0.05, 0.1, 0.2, 0.4]:
        for theta in [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]:
            kernel = cv2.getGaborKernel(
                (21, 21), sigma=4.0, theta=theta,
                lambd=1.0 / freq, gamma=0.5, psi=0
            )
            filtered = cv2.filter2D(gray, cv2.CV_64F, kernel)
            energies.append(np.mean(np.abs(filtered)))

    mean_energy = float(np.mean(energies))

    if mean_energy >= 10:
        score = 100.0
    elif mean_energy >= 5:
        score = 30 + (mean_energy - 5) / 5 * 70
    else:
        score = max(0, mean_energy / 5 * 30)

    return MetricResult(
        name="gabor_texture_energy",
        raw_value=round(mean_energy, 2),
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["gabor_texture_energy"],
    )


def _score_subject_dominance(img_bgr: np.ndarray) -> MetricResult:
    """Metric 11: Subject area percentage using spectral residual saliency.

    Detects how much of the image is "salient" (the main subject).
    For puzzles, we want the character small (<50%) with lots of scene detail.
    Pass: <50%, Fail: >65%

    Uses manual spectral residual implementation (no cv2.saliency dependency).
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float64)

    # Spectral residual saliency (manual implementation)
    # Resize to small fixed size for FFT efficiency
    small = cv2.resize(gray, (256, 256))
    # FFT
    f = np.fft.fft2(small)
    magnitude = np.abs(f)
    phase = np.angle(f)
    log_mag = np.log(magnitude + 1e-10)
    # Spectral residual = log magnitude - smoothed log magnitude
    smooth_mag = cv2.blur(log_mag, (3, 3))
    spectral_residual = log_mag - smooth_mag
    # Reconstruct saliency map
    saliency_complex = np.exp(spectral_residual) * np.exp(1j * phase)
    saliency_map = np.abs(np.fft.ifft2(saliency_complex)) ** 2
    # Gaussian blur for smoother saliency
    saliency_map = cv2.GaussianBlur(saliency_map.astype(np.float32), (9, 9), 2.5)
    # Normalize to 0-255
    saliency_norm = ((saliency_map - saliency_map.min()) /
                     (saliency_map.max() - saliency_map.min() + 1e-10) * 255).astype(np.uint8)

    _, binary = cv2.threshold(saliency_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    subject_pct = float(np.mean(binary > 0) * 100)

    if subject_pct <= 50:
        score = 100.0
    elif subject_pct <= 65:
        score = 100 - (subject_pct - 50) / 15 * 60
    else:
        score = max(0, 40 - (subject_pct - 65) / 15 * 40)

    return MetricResult(
        name="subject_dominance",
        raw_value=round(subject_pct, 1),
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["subject_dominance"],
    )


def _score_white_patch(img_bgr: np.ndarray) -> MetricResult:
    """Metric 12: Detect large near-pure-white patches — failed composite indicator.

    When the PIL composite background isn't blended away by Kontext Max, a clean
    white area remains around the character's feet/edges. This is the tell-tale
    sign of a seed where the model did almost nothing.

    Finds the largest connected region of near-pure white (all channels > 248)
    after a small erosion to remove single-pixel noise. Hard fails if that region
    covers >= 2% of the total image.

    Note: This threshold assumes non-snow scenes. A white building wall or bright
    sky won't typically produce a single connected blob of this size at pure white.
    """
    h, w = img_bgr.shape[:2]
    total_pixels = h * w

    # Near-pure white: all three channels > 248
    white_mask = np.all(img_bgr > 248, axis=2).astype(np.uint8)

    # Erode slightly to remove isolated noise pixels
    kernel = np.ones((3, 3), np.uint8)
    white_mask = cv2.erode(white_mask, kernel, iterations=1)

    # Find connected components
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(white_mask, connectivity=8)

    if num_labels <= 1:
        largest_pct = 0.0
    else:
        # stats rows: [label0=background, label1, ...]; column 4 = area
        areas = stats[1:, cv2.CC_STAT_AREA]
        largest_pct = float(np.max(areas)) / total_pixels * 100

    # Score: <0.5% = fine, >=2% = hard fail
    if largest_pct < 0.5:
        score = 100.0
    elif largest_pct < 2.0:
        score = 100 - (largest_pct - 0.5) / 1.5 * 100  # 100 → 0
    else:
        score = 0.0

    hard_fail = largest_pct >= 2.0
    return MetricResult(
        name="white_patch",
        raw_value=round(largest_pct, 2),
        normalized_score=round(max(0, min(100, score)), 1),
        weight=METRIC_WEIGHTS["white_patch"],
        hard_fail=hard_fail,
        hard_fail_reason=(
            f"White patch covers {largest_pct:.1f}% of image — composite not blended (failed seed)"
            if hard_fail else ""
        ),
    )


def score_transformation(source_path: str, generated_path: str) -> float:
    """Score how much the generated image differs from the source photo.

    Catches "barely transformed" outputs where the model didn't actually
    apply the cartoon style. Uses histogram comparison + structural difference.

    Returns:
        Score 0-100. Higher = more transformed (good).
        Below 30 means the model barely changed the image.
    """
    source = cv2.imread(source_path)
    generated = cv2.imread(generated_path)
    if source is None or generated is None:
        return 50.0  # neutral if can't compare

    # Resize both to same small size for fair comparison
    size = (256, 256)
    src_small = cv2.resize(source, size)
    gen_small = cv2.resize(generated, size)

    # Method 1: Histogram comparison (color distribution difference)
    # Convert to HSV for perceptually meaningful comparison
    src_hsv = cv2.cvtColor(src_small, cv2.COLOR_BGR2HSV)
    gen_hsv = cv2.cvtColor(gen_small, cv2.COLOR_BGR2HSV)

    hist_diffs = []
    for c in range(3):
        src_hist = cv2.calcHist([src_hsv], [c], None, [64], [0, 256])
        gen_hist = cv2.calcHist([gen_hsv], [c], None, [64], [0, 256])
        cv2.normalize(src_hist, src_hist)
        cv2.normalize(gen_hist, gen_hist)
        # Correlation: 1.0 = identical, 0.0 = no correlation, -1.0 = inverse
        corr = cv2.compareHist(src_hist, gen_hist, cv2.HISTCMP_CORREL)
        hist_diffs.append(corr)

    avg_correlation = float(np.mean(hist_diffs))

    # Method 2: Structural difference (pixel-level)
    src_gray = cv2.cvtColor(src_small, cv2.COLOR_BGR2GRAY).astype(np.float64)
    gen_gray = cv2.cvtColor(gen_small, cv2.COLOR_BGR2GRAY).astype(np.float64)
    # Normalized mean absolute difference
    pixel_diff = np.mean(np.abs(src_gray - gen_gray)) / 255.0

    # Combine: high correlation = barely changed, high pixel diff = well transformed
    # correlation 0.95+ with low pixel diff = model didn't transform
    # correlation <0.7 or high pixel diff = good transformation
    transform_signal = (1.0 - avg_correlation) * 60 + pixel_diff * 40

    # Scale to 0-100
    score = min(100, max(0, transform_signal * 200))
    return round(score, 1)


def score_puzzle_quality(
    image_path: str,
    puzzle_pieces: int = 1000,
    source_path: Optional[str] = None,
) -> PuzzleScore:
    """Score an image's suitability as a physical jigsaw puzzle.

    Runs 11 metrics on the image resized to 1500px long edge.
    Uses only numpy + opencv — no torch, no InsightFace.

    If source_path is provided, also runs a transformation check to detect
    images where the model barely changed the original photo.

    Args:
        image_path: Path to the image to score.
        puzzle_pieces: Target puzzle piece count (500 or 1000).
        source_path: Optional path to the original source photo.

    Returns:
        PuzzleScore with composite score, grade, per-metric details,
        hard fail reasons, and transformation_score.
    """
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        return PuzzleScore(
            composite=0.0,
            grade=PuzzleGrade.FAIL,
            hard_fail_reasons=["Could not read image"],
        )

    # Resize for consistent analysis
    img_bgr = _resize_for_analysis(img_bgr)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Piece window size scales with puzzle piece count
    piece_window = 48 if puzzle_pieces >= 1000 else 64

    # Run all 12 metrics
    metrics = [
        _score_flat_region_pct(gray, piece_window),
        _score_color_entropy(img_bgr),
        _score_edge_density(gray),
        _score_corner_detail_ratio(gray),
        _score_grid_uniformity(gray),
        _score_dominant_color_pct(img_bgr),
        _score_gradient_magnitude(gray),
        _score_hue_diversity(img_bgr),
        _score_laplacian_variance(gray),
        _score_gabor_texture_energy(gray),
        _score_subject_dominance(img_bgr),
        _score_white_patch(img_bgr),
    ]

    # Build per_metric dict and collect hard fails
    per_metric = {}
    hard_fail_reasons = []
    composite = 0.0

    for m in metrics:
        per_metric[m.name] = m
        composite += m.normalized_score * m.weight
        if m.hard_fail:
            hard_fail_reasons.append(m.hard_fail_reason)

    composite = round(composite, 1)

    # Transformation check (if source provided)
    transform_score = None
    if source_path:
        transform_score = score_transformation(source_path, image_path)
        if transform_score < 30:
            hard_fail_reasons.append(
                f"Image barely transformed from source (transform score {transform_score}/100, need >30)"
            )

    # Determine grade
    if hard_fail_reasons:
        grade = PuzzleGrade.HARD_FAIL
    elif composite >= 65:
        grade = PuzzleGrade.PASS
    elif composite >= 40:
        grade = PuzzleGrade.WARNING
    else:
        grade = PuzzleGrade.FAIL

    return PuzzleScore(
        composite=composite,
        grade=grade,
        per_metric=per_metric,
        hard_fail_reasons=hard_fail_reasons,
        transformation_score=transform_score,
    )


# Human-readable metric descriptions for UI display
METRIC_DESCRIPTIONS = {
    "flat_region_pct": "Flat regions — areas where all pieces look identical",
    "color_entropy": "Color entropy — richness of the color distribution",
    "edge_density": "Edge density — amount of detail boundaries",
    "corner_detail_ratio": "Corner detail — how much detail is in the corners vs center",
    "grid_uniformity": "Grid uniformity — how evenly detail is spread across the image",
    "dominant_color_pct": "Dominant color — whether one color takes over too much",
    "gradient_magnitude": "Texture gradients — presence of surface detail",
    "hue_diversity": "Hue diversity — number of distinct colors used",
    "laplacian_variance": "Sharpness — overall image clarity and detail",
    "gabor_texture_energy": "Texture richness — variety of surface patterns",
    "subject_dominance": "Subject size — whether character leaves room for scene",
    "white_patch": "White patch — detects unblended composite background (failed seed)",
}


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Score puzzle image quality (11 metrics).")
    parser.add_argument("image", help="Image to score")
    parser.add_argument("--pieces", type=int, default=1000, help="Target puzzle pieces")
    args = parser.parse_args()

    start = time.time()
    result = score_puzzle_quality(args.image, args.pieces)
    elapsed = time.time() - start

    print(f"Puzzle Quality Score: {result.composite}/100 — {result.grade.value}")
    print(f"Computed in {elapsed:.2f}s\n")

    print("Per-metric breakdown:")
    for name, m in result.per_metric.items():
        desc = METRIC_DESCRIPTIONS.get(name, name)
        flag = " *** HARD FAIL ***" if m.hard_fail else ""
        print(f"  {desc}")
        print(f"    Raw: {m.raw_value}  Score: {m.normalized_score}/100  Weight: {m.weight:.0%}{flag}")

    if result.hard_fail_reasons:
        print(f"\nHard fail reasons:")
        for reason in result.hard_fail_reasons:
            print(f"  - {reason}")
