"""Calibration script — optimize puzzle scorer weights using human labels.

Loads labeled images from output/calibration_labels.jsonl, runs the 11-metric
scorer on each, and uses scipy.optimize to find weights and thresholds that
maximize agreement with human labels.

Usage:
    python src/quality/calibrate.py
    python src/quality/calibrate.py --labels output/calibration_labels.jsonl
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from quality.puzzle_scorer import METRIC_WEIGHTS, score_puzzle_quality


LABELS_FILE = Path("output/calibration_labels.jsonl")

# Map human labels to numeric targets
LABEL_TO_SCORE = {
    "pass": 80,     # should score high
    "warning": 52,  # borderline
    "fail": 25,     # should score low
}


def load_labels(labels_path: str = str(LABELS_FILE)) -> List[Dict]:
    """Load labeled data from JSONL file."""
    labels = []
    with open(labels_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
                if "human_label" in entry and "per_metric" in entry:
                    labels.append(entry)
            except (json.JSONDecodeError, KeyError):
                continue
    return labels


def compute_agreement(labels: List[Dict], weights: Dict[str, float]) -> Tuple[float, float]:
    """Compute agreement between weighted scores and human labels.

    Returns:
        (mean_squared_error, classification_accuracy)
    """
    errors = []
    correct = 0
    total = 0

    for entry in labels:
        per_metric = entry["per_metric"]
        human_label = entry["human_label"]
        target = LABEL_TO_SCORE[human_label]

        # Compute weighted composite using provided weights
        composite = 0.0
        for metric_name, weight in weights.items():
            if metric_name in per_metric:
                composite += per_metric[metric_name]["score"] * weight

        errors.append((composite - target) ** 2)

        # Check classification accuracy
        if composite >= 65:
            predicted = "pass"
        elif composite >= 40:
            predicted = "warning"
        else:
            predicted = "fail"

        if predicted == human_label:
            correct += 1
        total += 1

    mse = float(np.mean(errors)) if errors else 999
    accuracy = correct / total if total > 0 else 0
    return mse, accuracy


def optimize_weights(labels: List[Dict]) -> Dict[str, float]:
    """Find optimal weights using scipy.optimize.

    Minimizes MSE between weighted composite and human label targets.
    Weights are constrained to sum to 1.0 and be non-negative.
    """
    try:
        from scipy.optimize import minimize
    except ImportError:
        print("scipy not installed — using current weights as baseline.")
        return METRIC_WEIGHTS

    metric_names = list(METRIC_WEIGHTS.keys())
    n = len(metric_names)

    def objective(w):
        weights = {metric_names[i]: w[i] for i in range(n)}
        mse, _ = compute_agreement(labels, weights)
        return mse

    # Start from current weights
    x0 = np.array([METRIC_WEIGHTS[name] for name in metric_names])

    # Constraints: sum to 1.0, each >= 0.01
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [(0.01, 0.50)] * n

    result = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints)

    if result.success:
        optimized = {metric_names[i]: round(result.x[i], 3) for i in range(n)}
        return optimized
    else:
        print(f"Optimization did not converge: {result.message}")
        return METRIC_WEIGHTS


def main():
    parser = argparse.ArgumentParser(description="Calibrate puzzle scorer weights.")
    parser.add_argument("--labels", default=str(LABELS_FILE))
    args = parser.parse_args()

    labels_path = Path(args.labels)
    if not labels_path.exists():
        print(f"No labels file found at {labels_path}")
        print("Run 'python src/quality/label_images.py' first to create labels.")
        sys.exit(1)

    labels = load_labels(str(labels_path))
    print(f"Loaded {len(labels)} labeled images")

    if len(labels) < 10:
        print(f"Need at least 10 labeled images for meaningful calibration (have {len(labels)})")
        sys.exit(1)

    # Current performance
    current_mse, current_acc = compute_agreement(labels, METRIC_WEIGHTS)
    print(f"\nCurrent weights performance:")
    print(f"  MSE: {current_mse:.1f}")
    print(f"  Classification accuracy: {current_acc:.1%}")

    # Optimize
    print(f"\nOptimizing weights...")
    optimized = optimize_weights(labels)

    opt_mse, opt_acc = compute_agreement(labels, optimized)
    print(f"\nOptimized weights performance:")
    print(f"  MSE: {opt_mse:.1f}")
    print(f"  Classification accuracy: {opt_acc:.1%}")

    # Show changes
    print(f"\nWeight changes:")
    print(f"  {'Metric':<25} {'Current':>8} {'Optimized':>10} {'Change':>8}")
    print(f"  {'-'*53}")
    for name in METRIC_WEIGHTS:
        current = METRIC_WEIGHTS[name]
        new = optimized.get(name, current)
        change = new - current
        marker = " *" if abs(change) > 0.02 else ""
        print(f"  {name:<25} {current:>8.3f} {new:>10.3f} {change:>+8.3f}{marker}")

    # Save optimized weights
    output_path = Path("output/calibrated_weights.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "weights": optimized,
            "metrics": {
                "mse": opt_mse,
                "accuracy": opt_acc,
                "n_labels": len(labels),
            },
            "comparison": {
                "current_mse": current_mse,
                "current_accuracy": current_acc,
            }
        }, f, indent=2)
    print(f"\nCalibrated weights saved to {output_path}")
    print("To apply: copy weights to METRIC_WEIGHTS in src/quality/puzzle_scorer.py")


if __name__ == "__main__":
    main()
