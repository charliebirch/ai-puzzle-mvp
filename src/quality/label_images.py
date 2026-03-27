"""Labeling CLI — manually label generated images for calibration.

Shows each generated image with its auto-score, asks the operator for
pass/warning/fail judgment. Saves labels to output/calibration_labels.jsonl.

Usage:
    python src/quality/label_images.py orders/*/generated.png
    python src/quality/label_images.py --dir orders/
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from quality.puzzle_scorer import score_puzzle_quality, METRIC_DESCRIPTIONS


LABELS_FILE = Path("output/calibration_labels.jsonl")


def label_image(image_path: str, puzzle_pieces: int = 1000) -> dict:
    """Score an image and prompt for human label.

    Opens the image in the default viewer, prints the auto-score,
    and asks for a human judgment.

    Returns:
        Dict with image_path, auto_score, human_label, and per_metric data.
    """
    print(f"\n{'='*60}")
    print(f"Image: {image_path}")

    # Auto-score
    result = score_puzzle_quality(image_path, puzzle_pieces)
    print(f"Auto score: {result.composite}/100 ({result.grade.value})")
    print(f"Per-metric:")
    for name, m in result.per_metric.items():
        desc = METRIC_DESCRIPTIONS.get(name, name)
        flag = " *** HARD FAIL ***" if m.hard_fail else ""
        print(f"  {desc}: {m.normalized_score}/100 (raw: {m.raw_value}){flag}")

    if result.hard_fail_reasons:
        print(f"Hard fails: {', '.join(result.hard_fail_reasons)}")

    # Open image for viewing
    try:
        subprocess.Popen(["open", image_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        print(f"  (Could not auto-open image — view it manually)")

    # Get human label
    while True:
        label = input("\nYour judgment [p]ass / [w]arning / [f]ail / [s]kip: ").strip().lower()
        if label in ("p", "pass"):
            human_label = "pass"
            break
        elif label in ("w", "warning"):
            human_label = "warning"
            break
        elif label in ("f", "fail"):
            human_label = "fail"
            break
        elif label in ("s", "skip"):
            return None
        else:
            print("  Enter p, w, f, or s")

    notes = input("Notes (optional): ").strip()

    return {
        "image_path": str(image_path),
        "auto_composite": result.composite,
        "auto_grade": result.grade.value,
        "human_label": human_label,
        "notes": notes,
        "per_metric": {
            name: {"raw": m.raw_value, "score": m.normalized_score}
            for name, m in result.per_metric.items()
        },
        "labeled_at": datetime.now().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Label puzzle images for calibration.")
    parser.add_argument("images", nargs="*", help="Image files to label")
    parser.add_argument("--dir", help="Directory to scan for generated.png files")
    parser.add_argument("--pieces", type=int, default=1000)
    args = parser.parse_args()

    # Collect image paths
    image_paths = list(args.images)
    if args.dir:
        for p in sorted(Path(args.dir).rglob("generated.png")):
            image_paths.append(str(p))

    if not image_paths:
        print("No images to label. Provide paths or --dir.")
        sys.exit(1)

    # Ensure output directory exists
    LABELS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Check for already-labeled images
    labeled = set()
    if LABELS_FILE.exists():
        with open(LABELS_FILE) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    labeled.add(entry["image_path"])
                except (json.JSONDecodeError, KeyError):
                    pass

    remaining = [p for p in image_paths if p not in labeled]
    print(f"Found {len(image_paths)} images, {len(labeled)} already labeled, {len(remaining)} to label.")

    labeled_count = 0
    for path in remaining:
        if not Path(path).exists():
            print(f"  Skipping {path} — file not found")
            continue

        result = label_image(path, args.pieces)
        if result is None:
            continue

        # Append to JSONL
        with open(LABELS_FILE, "a") as f:
            f.write(json.dumps(result) + "\n")
        labeled_count += 1
        print(f"  Saved ({labeled_count} labeled this session)")

    print(f"\nDone! {labeled_count} images labeled. Labels saved to {LABELS_FILE}")


if __name__ == "__main__":
    main()
