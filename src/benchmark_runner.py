"""
Benchmark runner: tests backends against test photos and styles.

Runs the full pipeline (generation + optional face swap + optional quality scoring)
and records detailed JSONL results for comparison.

Usage:
    # Baseline run: all 12 test photos, face swap + quality scoring, fixed seed
    python3 src/benchmark_runner.py --quality --face-swap --seed 42

    # Quick test on one photo, no quality scoring
    python3 src/benchmark_runner.py --photos input/Chaz/charlie-ny.jpeg --no-quality

    # Best-of-3 selection (generates 3 per photo, keeps highest quality)
    python3 src/benchmark_runner.py --quality --face-swap --seed 42 --best-of 3

    # Specific backend and style
    python3 src/benchmark_runner.py --backends flux_kontext --styles storybook_cartoon
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

import requests
from PIL import Image
from dotenv import load_dotenv

from backends.registry import get_backend, list_backends
from style_presets import STYLE_PRESETS, get_style

load_dotenv()

BENCHMARK_DIR = Path("output/benchmarks")
TEST_PHOTOS_FILE = Path("src/test_photos.json")


def load_test_photos() -> List[Dict]:
    """Load the curated test photo matrix from test_photos.json."""
    if not TEST_PHOTOS_FILE.exists():
        print(f"Warning: {TEST_PHOTOS_FILE} not found, falling back to directory scan.")
        return []
    with TEST_PHOTOS_FILE.open() as f:
        return json.load(f)


def find_test_photos(photo_args: Optional[List[str]] = None) -> List[str]:
    """Find test photos from args, test_photos.json, or by scanning input/ recursively."""
    if photo_args:
        return photo_args

    # Try curated test photo matrix first
    test_photos = load_test_photos()
    if test_photos:
        photos = [p["path"] for p in test_photos if Path(p["path"]).exists()]
        if photos:
            return sorted(photos)
        print("Warning: test_photos.json entries not found on disk, scanning input/.")

    # Fallback: recursive scan of input/
    input_dir = Path("input")
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    photos = [
        str(p) for p in input_dir.rglob("*")
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


def run_face_swap(photo_path: str, generated_path: str, output_path: str) -> Dict:
    """Run codeplugtech face swap and save result. Returns metadata dict."""
    from backends.easel_swap import face_swap

    start = time.time()
    swap_result = face_swap(
        swap_image_path=photo_path,
        target_image_path=generated_path,
    )
    elapsed = time.time() - start

    response = requests.get(swap_result.image_url, timeout=120)
    response.raise_for_status()
    swapped_img = Image.open(BytesIO(response.content))
    swapped_img.save(output_path, quality=95)

    return {
        "status": "ok",
        "elapsed_seconds": round(elapsed, 1),
        "cost_estimate": swap_result.cost_estimate,
        "model_id": swap_result.model_id,
        "output_size": list(swapped_img.size),
    }


def run_quality_scoring(generated_path: str, source_path: str) -> Dict:
    """Run quality assessment. Returns the full quality dict."""
    from quality import assess_quality
    return assess_quality(
        generated_path=generated_path,
        source_path=source_path,
    )


def run_single_benchmark(
    backend_name: str,
    photo_path: str,
    style_id: str,
    subject: str,
    output_dir: Path,
    do_face_swap: bool = False,
    do_quality: bool = False,
    do_preprocess: bool = False,
    seed: Optional[int] = None,
    run_index: int = 0,
) -> dict:
    """Run a single benchmark: one backend + one photo + one style.

    Args:
        backend_name: Backend identifier.
        photo_path: Path to the input photo.
        style_id: Style preset to use.
        subject: Subject description (unused by current prompts, kept for metadata).
        output_dir: Directory to save output images.
        do_face_swap: Whether to run face swap after generation.
        do_quality: Whether to run quality scoring.
        do_preprocess: Whether to run face alignment preprocessing.
        seed: Fixed seed for reproducibility (None = random).
        run_index: Index for best-of-N runs (0-based).

    Returns:
        Dict with all benchmark data.
    """
    backend = get_backend(backend_name)
    style = get_style(style_id)

    prompt = style["kontext_prompt"]

    # Check if this style disables face swap
    style_face_swap = style.get("face_swap", True)
    actual_face_swap = do_face_swap and style_face_swap

    photo_stem = Path(photo_path).stem
    suffix = f"_run{run_index}" if run_index > 0 else ""
    output_name = f"{backend_name}_{style_id}_{photo_stem}{suffix}.png"
    output_path = output_dir / output_name

    # Preprocess: face alignment (optional, $0 local processing)
    actual_photo_path = photo_path
    preprocess_data = None
    if do_preprocess:
        from preprocess import align_and_crop
        aligned_path = str(output_dir / f"{photo_stem}{suffix}_aligned.jpg")
        preprocess_data = align_and_crop(
            image_path=photo_path,
            output_path=aligned_path,
        )
        if preprocess_data["status"] == "aligned":
            actual_photo_path = aligned_path

    # Use different seed per run_index for best-of-N
    actual_seed = (seed + run_index) if seed is not None else None

    record = {
        "timestamp": datetime.now().isoformat(),
        "backend": backend_name,
        "model_id": backend.replicate_id,
        "photo": photo_path,
        "photo_stem": photo_stem,
        "style": style_id,
        "subject": subject,
        "prompt": prompt,
        "seed": actual_seed,
        "run_index": run_index,
        "face_swap_enabled": actual_face_swap,
        "quality_enabled": do_quality,
        "preprocess_enabled": do_preprocess,
        "preprocess": preprocess_data,
        "cost_estimate": backend.cost_per_run,
    }

    start = time.time()
    try:
        # Step 1: Generate (use preprocessed photo if available)
        gen_start = time.time()
        gen_kwargs = {"seed": actual_seed}
        # Pass PuLID-specific settings if the style has them
        if "pulid_settings" in style:
            gen_kwargs["pulid_settings"] = style["pulid_settings"]
        result = backend.generate(
            prompt=prompt,
            image_path=actual_photo_path,
            style_settings=style["settings"],
            negative_prompt=style.get("negative_prompt"),
            **gen_kwargs,
        )
        gen_elapsed = time.time() - gen_start

        img = download_image(result.image_url, str(output_path))

        record.update({
            "status": "success",
            "generation_seconds": round(gen_elapsed, 1),
            "output_path": str(output_path),
            "output_size": list(img.size),
            "image_url": result.image_url,
        })

        total_cost = backend.cost_per_run

        # Step 2: Face swap (optional)
        if actual_face_swap:
            try:
                swap_output_name = f"{backend_name}_{style_id}_{photo_stem}{suffix}_swapped.png"
                swap_output_path = output_dir / swap_output_name
                swap_data = run_face_swap(photo_path, str(output_path), str(swap_output_path))
                record["face_swap"] = swap_data
                total_cost += swap_data["cost_estimate"]
                # Quality scoring should use the swapped image
                final_image_path = str(swap_output_path)
                record["final_image_path"] = final_image_path
            except Exception as e:
                record["face_swap"] = {"status": "error", "error": str(e)}
                final_image_path = str(output_path)
                record["final_image_path"] = final_image_path
        else:
            final_image_path = str(output_path)
            record["final_image_path"] = final_image_path

        # Step 3: Quality scoring (optional)
        if do_quality:
            try:
                quality = run_quality_scoring(final_image_path, photo_path)
                record["quality"] = quality
            except Exception as e:
                record["quality"] = {"status": "error", "error": str(e)}

        elapsed = time.time() - start
        record["total_elapsed_seconds"] = round(elapsed, 1)
        record["total_cost_estimate"] = round(total_cost, 4)

        # Print summary line
        composite = record.get("quality", {}).get("composite_score", "n/a")
        face_sim = record.get("quality", {}).get("face_similarity_raw", "n/a")
        swap_tag = "+swap" if actual_face_swap else ""
        qual_tag = f" Q={composite}" if do_quality else ""
        face_tag = f" F={face_sim:.2f}" if isinstance(face_sim, float) else ""
        print(f"  OK  {backend_name}{swap_tag}/{style_id}/{photo_stem}{suffix} ({elapsed:.1f}s ${total_cost:.3f}){qual_tag}{face_tag}")

    except Exception as e:
        elapsed = time.time() - start
        record.update({
            "status": "error",
            "total_elapsed_seconds": round(elapsed, 1),
            "error": str(e),
        })
        print(f"  FAIL {backend_name}/{style_id}/{photo_stem}{suffix}: {e}")

    return record


class _NumpySafeEncoder(json.JSONEncoder):
    """Handle numpy types that aren't JSON-serializable."""
    def default(self, obj):
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def append_result(record: dict, results_file: Path):
    """Append a benchmark result to the JSONL file."""
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with results_file.open("a") as f:
        f.write(json.dumps(record, cls=_NumpySafeEncoder) + "\n")


def run_benchmarks(
    backends: List[str],
    photos: List[str],
    styles: List[str],
    subject: str,
    do_face_swap: bool = False,
    do_quality: bool = False,
    do_preprocess: bool = False,
    seed: Optional[int] = None,
    best_of: int = 1,
    run_label: Optional[str] = None,
):
    """Run the full benchmark matrix.

    Args:
        backends: List of backend names to test.
        photos: List of photo paths.
        styles: List of style IDs.
        subject: Subject description.
        do_face_swap: Whether to run face swap after each generation.
        do_quality: Whether to run quality scoring.
        do_preprocess: Whether to run face alignment preprocessing.
        seed: Base seed for reproducibility.
        best_of: Generate N images per combo, keep the best (requires --quality).
        run_label: Optional label for this benchmark run.
    """
    total_combos = len(backends) * len(photos) * len(styles)
    total_runs = total_combos * best_of

    # Cost estimate per run
    swap_cost = 0.003 if do_face_swap else 0
    cost_per_run = sum(get_backend(b).cost_per_run for b in backends) / len(backends) + swap_cost
    estimated_cost = cost_per_run * total_runs

    # Create output directory with timestamp and label
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{timestamp}_{run_label}" if run_label else timestamp
    output_dir = BENCHMARK_DIR / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    results_file = output_dir / "results.jsonl"

    print(f"Benchmark: {len(backends)} backends x {len(photos)} photos x {len(styles)} styles = {total_combos} combos")
    if best_of > 1:
        print(f"Best-of-{best_of}: {total_runs} total runs")
    print(f"Face swap: {'on' if do_face_swap else 'off'} | Quality: {'on' if do_quality else 'off'} | Preprocess: {'on' if do_preprocess else 'off'} | Seed: {seed or 'random'}")
    print(f"Estimated cost: ${estimated_cost:.2f}")
    print(f"Output: {output_dir}")
    print(f"Results: {results_file}")
    print()

    # Save run config for reproducibility
    config = {
        "timestamp": datetime.now().isoformat(),
        "label": run_label,
        "backends": backends,
        "styles": styles,
        "photos": photos,
        "subject": subject,
        "face_swap": do_face_swap,
        "quality": do_quality,
        "preprocess": do_preprocess,
        "seed": seed,
        "best_of": best_of,
        "estimated_cost": estimated_cost,
    }
    with (output_dir / "config.json").open("w") as f:
        json.dump(config, f, indent=2)

    completed = 0
    errors = 0
    total_cost = 0.0
    best_results = []  # For best-of-N summary

    for backend_name in backends:
        for photo_path in photos:
            for style_id in styles:
                run_records = []

                for run_idx in range(best_of):
                    record = run_single_benchmark(
                        backend_name=backend_name,
                        photo_path=photo_path,
                        style_id=style_id,
                        subject=subject,
                        output_dir=output_dir,
                        do_face_swap=do_face_swap,
                        do_quality=do_quality,
                        do_preprocess=do_preprocess,
                        seed=seed,
                        run_index=run_idx,
                    )
                    append_result(record, results_file)

                    if record["status"] == "success":
                        completed += 1
                        total_cost += record.get("total_cost_estimate", 0)
                        run_records.append(record)
                    else:
                        errors += 1

                # Best-of-N: pick the run with highest composite score
                if best_of > 1 and run_records and do_quality:
                    scored = [r for r in run_records if r.get("quality", {}).get("composite_score") is not None]
                    if scored:
                        best = max(scored, key=lambda r: r["quality"]["composite_score"])
                        best_results.append(best)
                        print(f"    Best: run{best['run_index']} (Q={best['quality']['composite_score']})")

    print()
    print(f"Done: {completed} succeeded, {errors} failed, ~${total_cost:.2f} spent")
    print(f"Results: {results_file}")

    if best_of > 1 and best_results:
        avg_score = sum(r["quality"]["composite_score"] for r in best_results) / len(best_results)
        print(f"Best-of-{best_of} average composite: {avg_score:.1f}")

    # Also symlink as latest for easy access
    latest_link = BENCHMARK_DIR / "latest"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(output_dir.name)
    print(f"Symlinked: {latest_link} -> {output_dir.name}")


def parse_args():
    all_backends = sorted(list_backends().keys())
    all_styles = sorted(STYLE_PRESETS.keys())

    parser = argparse.ArgumentParser(
        description="Run AI puzzle benchmark matrix.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Baseline: all test photos, face swap + quality, fixed seed
  python3 src/benchmark_runner.py --quality --face-swap --seed 42

  # Quick test on one photo
  python3 src/benchmark_runner.py --photos input/Chaz/charlie-ny.jpeg

  # Best-of-3 with quality scoring
  python3 src/benchmark_runner.py --quality --face-swap --seed 42 --best-of 3

  # Label a run for easy comparison
  python3 src/benchmark_runner.py --quality --face-swap --seed 42 --label baseline
""",
    )
    parser.add_argument(
        "--backends", nargs="+", default=all_backends, choices=all_backends,
        help="Backends to test (default: all)",
    )
    parser.add_argument(
        "--styles", nargs="+", default=["storybook_cartoon"],
        help="Styles to test (default: storybook_cartoon)",
    )
    parser.add_argument(
        "--photos", nargs="+", default=None,
        help="Photo paths to test (default: test_photos.json or input/ scan)",
    )
    parser.add_argument(
        "--subject", default="a smiling person",
        help="Subject description for prompts",
    )

    # New flags
    parser.add_argument(
        "--face-swap", action="store_true", default=False,
        help="Run codeplugtech face swap after generation",
    )
    parser.add_argument(
        "--no-face-swap", action="store_true", default=False,
        help="Explicitly disable face swap (default behavior)",
    )
    parser.add_argument(
        "--quality", action="store_true", default=False,
        help="Run quality scoring (requires InsightFace)",
    )
    parser.add_argument(
        "--no-quality", action="store_true", default=False,
        help="Skip quality scoring (default behavior)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Fixed seed for reproducible generation",
    )
    parser.add_argument(
        "--best-of", type=int, default=1, metavar="N",
        help="Generate N images per combo, keep highest quality (requires --quality)",
    )
    parser.add_argument(
        "--preprocess", action="store_true", default=False,
        help="Run face alignment preprocessing before generation ($0, local)",
    )
    parser.add_argument(
        "--label", default=None,
        help="Label for this benchmark run (used in output directory name)",
    )

    args = parser.parse_args()

    # Resolve face-swap flag (--face-swap wins over default off, --no-face-swap overrides)
    if args.no_face_swap:
        args.do_face_swap = False
    else:
        args.do_face_swap = args.face_swap

    # Resolve quality flag
    if args.no_quality:
        args.do_quality = False
    else:
        args.do_quality = args.quality

    # Best-of-N requires quality scoring
    if args.best_of > 1 and not args.do_quality:
        parser.error("--best-of requires --quality (need scores to pick the best)")

    return args


if __name__ == "__main__":
    args = parse_args()
    photos = find_test_photos(args.photos)
    print(f"Test photos ({len(photos)}):")
    for p in photos:
        print(f"  {p}")
    print()
    run_benchmarks(
        backends=args.backends,
        photos=photos,
        styles=args.styles,
        subject=args.subject,
        do_face_swap=args.do_face_swap,
        do_quality=args.do_quality,
        do_preprocess=args.preprocess,
        seed=args.seed,
        best_of=args.best_of,
        run_label=args.label,
    )
