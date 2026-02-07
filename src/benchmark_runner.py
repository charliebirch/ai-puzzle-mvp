"""
Benchmark runner: tests backends against test photos and styles.

Usage:
    python src/benchmark_runner.py
    python src/benchmark_runner.py --backends flux_kontext --styles fairytale
    python src/benchmark_runner.py --photos input/test1.jpg input/test2.jpg
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List

import requests
from PIL import Image
from dotenv import load_dotenv

from backends.registry import get_backend, list_backends
from style_presets import STYLE_PRESETS, get_style

load_dotenv()

BENCHMARK_DIR = Path("output/benchmarks")
RESULTS_FILE = BENCHMARK_DIR / "benchmark_results.jsonl"


def find_test_photos(photo_args: List[str] = None) -> List[str]:
    """Find test photos from args or by scanning input/."""
    if photo_args:
        return photo_args

    input_dir = Path("input")
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    photos = [
        str(p) for p in input_dir.iterdir()
        if p.suffix.lower() in extensions and not p.name.startswith(".")
    ]
    if not photos:
        print("No test photos found in input/. Add photos or use --photos.")
        sys.exit(1)
    return sorted(photos)


def download_image(url: str, save_path: str) -> Image.Image:
    """Download an image from URL and save it."""
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content))
    img.save(save_path, quality=95)
    return img


def run_single_benchmark(
    backend_name: str,
    photo_path: str,
    style_id: str,
    subject: str,
    output_dir: Path,
) -> dict:
    """Run a single benchmark: one backend + one photo + one style."""
    backend = get_backend(backend_name)
    style = get_style(style_id)

    prompt = style["kontext_prompt"]

    photo_stem = Path(photo_path).stem
    output_name = f"{backend_name}_{style_id}_{photo_stem}.png"
    output_path = output_dir / output_name

    record = {
        "timestamp": datetime.now().isoformat(),
        "backend": backend_name,
        "model_id": backend.replicate_id,
        "photo": photo_path,
        "photo_stem": photo_stem,
        "style": style_id,
        "subject": subject,
        "prompt": prompt,
        "supports_face_lock": backend.supports_face_lock,
        "cost_estimate": backend.cost_per_run,
    }

    start = time.time()
    try:
        result = backend.generate(
            prompt=prompt,
            image_path=photo_path,
            style_settings=style["settings"],
            negative_prompt=style.get("negative_prompt"),
        )
        elapsed = time.time() - start

        img = download_image(result.image_url, str(output_path))

        record.update({
            "status": "success",
            "elapsed_seconds": round(elapsed, 1),
            "output_path": str(output_path),
            "output_size": list(img.size),
            "image_url": result.image_url,
        })
        print(f"  OK  {backend_name}/{style_id}/{photo_stem} ({elapsed:.1f}s)")

    except Exception as e:
        elapsed = time.time() - start
        record.update({
            "status": "error",
            "elapsed_seconds": round(elapsed, 1),
            "error": str(e),
        })
        print(f"  FAIL {backend_name}/{style_id}/{photo_stem}: {e}")

    return record


def append_result(record: dict):
    """Append a benchmark result to the JSONL file."""
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_FILE.open("a") as f:
        f.write(json.dumps(record) + "\n")


def run_benchmarks(
    backends: List[str],
    photos: List[str],
    styles: List[str],
    subject: str,
):
    """Run the full benchmark matrix."""
    total = len(backends) * len(photos) * len(styles)
    estimated_cost = sum(get_backend(b).cost_per_run for b in backends) * len(photos) * len(styles)

    print(f"Benchmark matrix: {len(backends)} backends x {len(photos)} photos x {len(styles)} styles = {total} runs")
    print(f"Estimated cost: ${estimated_cost:.2f}")
    print(f"Results: {RESULTS_FILE}")
    print()

    output_dir = BENCHMARK_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    errors = 0
    total_cost = 0.0

    for backend_name in backends:
        for photo_path in photos:
            for style_id in styles:
                record = run_single_benchmark(
                    backend_name=backend_name,
                    photo_path=photo_path,
                    style_id=style_id,
                    subject=subject,
                    output_dir=output_dir,
                )
                append_result(record)

                if record["status"] == "success":
                    completed += 1
                    total_cost += record.get("cost_estimate", 0)
                else:
                    errors += 1

    print()
    print(f"Done: {completed} succeeded, {errors} failed, ~${total_cost:.2f} spent")
    print(f"Results saved to {RESULTS_FILE}")


def parse_args():
    all_backends = sorted(list_backends().keys())
    all_styles = sorted(STYLE_PRESETS.keys())

    parser = argparse.ArgumentParser(description="Run AI puzzle benchmark matrix.")
    parser.add_argument(
        "--backends",
        nargs="+",
        default=all_backends,
        choices=all_backends,
        help="Backends to test (default: all)",
    )
    parser.add_argument(
        "--styles",
        nargs="+",
        default=["fairytale", "storybook_cartoon"],
        choices=all_styles,
        help="Styles to test (default: fairytale, storybook_cartoon)",
    )
    parser.add_argument(
        "--photos",
        nargs="+",
        default=None,
        help="Photo paths to test (default: all in input/)",
    )
    parser.add_argument(
        "--subject",
        default="a smiling person",
        help="Subject description for prompts",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    photos = find_test_photos(args.photos)
    print(f"Test photos: {photos}")
    run_benchmarks(
        backends=args.backends,
        photos=photos,
        styles=args.styles,
        subject=args.subject,
    )
