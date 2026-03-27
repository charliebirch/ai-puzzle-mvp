"""Puzzle quality heatmap — visual overlay showing problem regions.

Divides image into a piece-sized grid, computes per-cell quality
(local variance + color entropy + edge density), and generates a
color-coded overlay: green (good) → yellow (weak) → red (dead zone).

Also returns a JSON-serializable grid of cell scores for the web UI.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


def generate_heatmap(
    image_path: str,
    output_path: str,
    grid_size: Tuple[int, int] = (8, 6),
) -> Dict:
    """Generate a puzzle quality heatmap overlay.

    Args:
        image_path: Path to the image to analyze.
        output_path: Path to save the heatmap overlay image.
        grid_size: (cols, rows) for the analysis grid. Default 8x6.

    Returns:
        Dict with 'grid_scores' (2D list of cell scores 0-100),
        'min_cell' (worst cell score), 'mean_cell' (average),
        and 'problem_regions' (list of {row, col, score, reason}).
    """
    img = cv2.imread(image_path)
    if img is None:
        return {"error": "Could not read image"}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    cols, rows = grid_size
    cell_h = h // rows
    cell_w = w // cols

    grid_scores = []
    problem_regions = []

    for r in range(rows):
        row_scores = []
        for c in range(cols):
            y1, y2 = r * cell_h, (r + 1) * cell_h
            x1, x2 = c * cell_w, (c + 1) * cell_w
            cell_gray = gray[y1:y2, x1:x2]
            cell_bgr = img[y1:y2, x1:x2]

            # Compute cell quality from 3 signals
            variance_score = _cell_variance_score(cell_gray)
            entropy_score = _cell_entropy_score(cell_bgr)
            edge_score = _cell_edge_score(cell_gray)

            # Weighted blend
            cell_score = (
                variance_score * 0.40
                + entropy_score * 0.35
                + edge_score * 0.25
            )
            cell_score = round(max(0, min(100, cell_score)), 1)
            row_scores.append(cell_score)

            # Flag problem regions
            if cell_score < 40:
                reason = _diagnose_cell(variance_score, entropy_score, edge_score)
                problem_regions.append({
                    "row": r, "col": c, "score": cell_score, "reason": reason,
                })

        grid_scores.append(row_scores)

    # Generate overlay image
    overlay = img.copy()
    for r in range(rows):
        for c in range(cols):
            y1, y2 = r * cell_h, (r + 1) * cell_h
            x1, x2 = c * cell_w, (c + 1) * cell_w
            score = grid_scores[r][c]

            # Color: green (good) → yellow (ok) → red (bad)
            color = _score_to_color(score)

            # Semi-transparent overlay
            cell_overlay = overlay[y1:y2, x1:x2].copy()
            cell_color = np.full_like(cell_overlay, color)
            alpha = 0.35
            cv2.addWeighted(cell_color, alpha, cell_overlay, 1 - alpha, 0, overlay[y1:y2, x1:x2])

            # Grid lines
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 255), 1)

            # Score text
            text = f"{score:.0f}"
            font_scale = min(cell_w, cell_h) / 120
            thickness = max(1, int(font_scale * 2))
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
            tx = x1 + (cell_w - text_size[0]) // 2
            ty = y1 + (cell_h + text_size[1]) // 2
            # Black outline for readability
            cv2.putText(overlay, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale, (0, 0, 0), thickness + 2)
            cv2.putText(overlay, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale, (255, 255, 255), thickness)

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output_path, overlay)

    all_scores = [s for row in grid_scores for s in row]
    return {
        "grid_scores": grid_scores,
        "min_cell": round(min(all_scores), 1),
        "mean_cell": round(float(np.mean(all_scores)), 1),
        "max_cell": round(max(all_scores), 1),
        "problem_regions": problem_regions,
        "heatmap_path": output_path,
    }


def _cell_variance_score(cell_gray: np.ndarray) -> float:
    """Score cell based on local luminance variance. 0-100."""
    var = float(np.var(cell_gray))
    # variance < 100 is flat, > 800 is very detailed
    if var >= 800:
        return 100.0
    elif var >= 200:
        return 50 + (var - 200) / 600 * 50
    elif var >= 100:
        return 20 + (var - 100) / 100 * 30
    else:
        return max(0, var / 100 * 20)


def _cell_entropy_score(cell_bgr: np.ndarray) -> float:
    """Score cell based on color entropy. 0-100."""
    entropies = []
    for c in range(3):
        hist, _ = np.histogram(cell_bgr[:, :, c].flatten(), bins=64, range=(0, 256))
        hist = hist / hist.sum()
        hist = hist[hist > 0]
        entropy = -np.sum(hist * np.log2(hist))
        entropies.append(entropy)
    avg = float(np.mean(entropies))
    # Max entropy for 64 bins is 6.0, good cell is >4.0
    return min(100, max(0, avg / 5.0 * 100))


def _cell_edge_score(cell_gray: np.ndarray) -> float:
    """Score cell based on edge density. 0-100."""
    edges = cv2.Canny(cell_gray, 50, 150)
    density = np.mean(edges > 0) * 100
    # 5-15% is good
    if 5 <= density <= 15:
        return 100.0
    elif density < 5:
        return max(0, density / 5 * 80)
    else:
        return max(0, 100 - (density - 15) * 3)


def _score_to_color(score: float) -> Tuple[int, int, int]:
    """Convert score 0-100 to BGR color: red → yellow → green."""
    if score >= 70:
        # Green to yellow-green
        t = (score - 70) / 30
        return (0, 255, int(255 * (1 - t)))  # BGR
    elif score >= 40:
        # Yellow to orange
        t = (score - 40) / 30
        return (0, int(180 + 75 * t), 255)  # BGR
    else:
        # Orange to red
        t = score / 40
        return (0, int(80 * t), 255)  # BGR


def _diagnose_cell(variance_score: float, entropy_score: float, edge_score: float) -> str:
    """Diagnose why a cell scored low."""
    issues = []
    if variance_score < 30:
        issues.append("flat/uniform area")
    if entropy_score < 30:
        issues.append("low color variety")
    if edge_score < 30:
        issues.append("no detail/edges")
    return ", ".join(issues) if issues else "low overall quality"


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Generate puzzle quality heatmap.")
    parser.add_argument("image", help="Image to analyze")
    parser.add_argument("--output", "-o", default="heatmap.png", help="Output path")
    parser.add_argument("--cols", type=int, default=8, help="Grid columns")
    parser.add_argument("--rows", type=int, default=6, help="Grid rows")
    args = parser.parse_args()

    result = generate_heatmap(args.image, args.output, (args.cols, args.rows))
    print(json.dumps(result, indent=2, default=str))
    print(f"\nHeatmap saved to {args.output}")
