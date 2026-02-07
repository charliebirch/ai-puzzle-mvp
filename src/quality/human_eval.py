"""
Human evaluation CLI for AI puzzle outputs.

Displays generated images and collects 1-5 scores for:
- Face recognizability
- Art quality
- Style adherence
- Puzzle suitability

Saves results to output/benchmarks/human_eval_scores.jsonl
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

EVAL_FILE = Path("output/benchmarks/human_eval_scores.jsonl")

CATEGORIES = [
    ("face_recognizability", "Face Recognizability - Can you identify the person from the original photo?"),
    ("art_quality", "Art Quality - Is the image well-rendered with good detail/composition?"),
    ("style_adherence", "Style Adherence - Does it match the intended style (fairytale, cartoon, etc)?"),
    ("puzzle_suitability", "Puzzle Suitability - Would this work well as a physical jigsaw puzzle?"),
]


def _get_score(prompt: str) -> int:
    """Get a 1-5 score from the user."""
    while True:
        try:
            value = input(f"  {prompt} (1-5): ").strip()
            score = int(value)
            if 1 <= score <= 5:
                return score
            print("  Please enter a number between 1 and 5.")
        except ValueError:
            print("  Please enter a number between 1 and 5.")
        except (EOFError, KeyboardInterrupt):
            print("\nEvaluation cancelled.")
            sys.exit(0)


def evaluate_image(
    image_path: str,
    source_photo: Optional[str] = None,
    backend: Optional[str] = None,
    style: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """Collect human evaluation scores for a single image."""
    print(f"\nEvaluating: {image_path}")
    if source_photo:
        print(f"  Source: {source_photo}")
    if backend:
        print(f"  Backend: {backend}")
    if style:
        print(f"  Style: {style}")
    print()

    # Open image for viewing (macOS)
    try:
        import subprocess
        subprocess.Popen(["open", image_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if source_photo:
            subprocess.Popen(["open", source_photo], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        print(f"  (Open {image_path} manually to view)")

    scores = {}
    for key, description in CATEGORIES:
        scores[key] = _get_score(description)

    # Optional written notes
    user_notes = input("  Notes (optional, press Enter to skip): ").strip()

    record = {
        "timestamp": datetime.now().isoformat(),
        "image_path": image_path,
        "source_photo": source_photo,
        "backend": backend,
        "style": style,
        "scores": scores,
        "average": round(sum(scores.values()) / len(scores), 2),
        "notes": user_notes or notes or "",
    }

    return record


def save_evaluation(record: dict):
    """Append an evaluation record to the JSONL file."""
    EVAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with EVAL_FILE.open("a") as f:
        f.write(json.dumps(record) + "\n")


def evaluate_directory(
    directory: str,
    source_photo: Optional[str] = None,
):
    """Evaluate all images in a directory."""
    dir_path = Path(directory)
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    images = sorted(p for p in dir_path.iterdir() if p.suffix.lower() in extensions)

    if not images:
        print(f"No images found in {directory}")
        return

    print(f"Found {len(images)} images to evaluate in {directory}")
    print("=" * 60)

    for i, img_path in enumerate(images, 1):
        print(f"\n--- Image {i}/{len(images)} ---")

        # Try to infer backend and style from filename
        name = img_path.stem
        backend = None
        style = None
        for b in ["flux_kontext"]:
            if b in name:
                backend = b
                break
        for s in ["fairytale", "superhero", "pixel_quest", "storybook_cartoon"]:
            if s in name:
                style = s
                break

        record = evaluate_image(
            image_path=str(img_path),
            source_photo=source_photo,
            backend=backend,
            style=style,
        )
        save_evaluation(record)
        print(f"  Saved! Average: {record['average']}/5")

    print(f"\nAll evaluations saved to {EVAL_FILE}")


def print_summary():
    """Print summary of all human evaluations."""
    if not EVAL_FILE.exists():
        print("No evaluations found.")
        return

    records = []
    with EVAL_FILE.open() as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    if not records:
        print("No evaluations found.")
        return

    print(f"Human Evaluation Summary ({len(records)} evaluations)")
    print("=" * 60)

    # Group by backend
    by_backend = {}
    for r in records:
        b = r.get("backend", "unknown")
        by_backend.setdefault(b, []).append(r)

    for backend, evals in sorted(by_backend.items()):
        avg_scores = {cat: 0.0 for cat, _ in CATEGORIES}
        for e in evals:
            for cat, _ in CATEGORIES:
                avg_scores[cat] += e["scores"].get(cat, 0)
        for cat in avg_scores:
            avg_scores[cat] /= len(evals)

        overall = sum(avg_scores.values()) / len(avg_scores)
        print(f"\n  {backend} ({len(evals)} evals, avg: {overall:.1f}/5)")
        for cat, desc in CATEGORIES:
            print(f"    {cat}: {avg_scores[cat]:.1f}/5")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Human evaluation of AI puzzle outputs.")
    sub = parser.add_subparsers(dest="command")

    eval_p = sub.add_parser("eval", help="Evaluate images in a directory")
    eval_p.add_argument("directory", help="Directory containing images to evaluate")
    eval_p.add_argument("--source", default=None, help="Original source photo for comparison")

    single_p = sub.add_parser("single", help="Evaluate a single image")
    single_p.add_argument("image", help="Image to evaluate")
    single_p.add_argument("--source", default=None, help="Original source photo")
    single_p.add_argument("--backend", default=None)
    single_p.add_argument("--style", default=None)

    summary_p = sub.add_parser("summary", help="Print evaluation summary")

    args = parser.parse_args()

    if args.command == "eval":
        evaluate_directory(args.directory, args.source)
    elif args.command == "single":
        record = evaluate_image(args.image, args.source, args.backend, args.style)
        save_evaluation(record)
        print(f"Saved! Average: {record['average']}/5")
    elif args.command == "summary":
        print_summary()
    else:
        parser.print_help()
