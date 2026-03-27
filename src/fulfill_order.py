"""
Order fulfillment CLI - single command to process a customer order end-to-end.

Usage:
    python src/fulfill_order.py --photo customer.jpg --style animation_village \
        --subject "a young girl" --puzzle-size 1000 --order-id ETSY-12345

    python src/fulfill_order.py --photo customer.jpg --style cartoon_village \
        --subject "a young man" --puzzle-size 500 --order-id ETSY-67890 --skip-consent

Supports auto-retry: if puzzle quality fails, adjusts prompt and retries
(up to --max-attempts, default 1 for CLI).
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from dotenv import load_dotenv
from PIL import Image, ImageOps

load_dotenv()

# Lightweight mode: skip quality scoring (InsightFace) and upscaling to save memory.
# Set LIGHTWEIGHT_MODE=1 on Render or other memory-constrained environments.
LIGHTWEIGHT_MODE = os.environ.get("LIGHTWEIGHT_MODE", "").strip() in ("1", "true", "yes")


def _generate_image(
    be, prompt, image_path, style_config, backend, seed, order_dir, pipeline,
    progress_callback, total_steps,
):
    """Run the AI generation pipeline (single-step or two-step).

    Returns (generated_path, total_cost, manifest_step_data).
    """
    import requests
    from io import BytesIO

    def _progress(step, label):
        if progress_callback:
            progress_callback(step, label, total_steps)

    if pipeline == "cartoonify_then_kontext":
        # Two-step pipeline: Cartoonify → Kontext Pro scene placement
        from backends.registry import get_backend

        # Step 3a: Cartoonify
        _progress(3, "Cartoonifying...")
        print("  Step 1: Cartoonifying photo...")
        cartoonify_be = get_backend("flux_cartoonify")
        start = time.time()
        cartoon_result = cartoonify_be.generate(
            prompt="",
            image_path=image_path,
            style_settings={},
        )
        cartoon_elapsed = time.time() - start

        response = requests.get(cartoon_result.image_url, timeout=120)
        response.raise_for_status()
        cartoon_img = Image.open(BytesIO(response.content))
        cartoonified_path = str(order_dir / "cartoonified.png")
        cartoon_img.save(cartoonified_path, quality=95)
        print(f"  Cartoonified {cartoon_img.size[0]}x{cartoon_img.size[1]} in {cartoon_elapsed:.1f}s (${cartoon_result.cost_estimate})")

        # Step 3b: Scene placement
        _progress(3, "Creating scene...")
        print(f"  Step 2: Scene placement ({backend})...")
        start = time.time()
        result = be.generate(
            prompt=prompt,
            image_path=cartoonified_path,
            style_settings={},
            negative_prompt=style_config.get("negative_prompt"),
            seed=seed,
        )
        scene_elapsed = time.time() - start

        elapsed = cartoon_elapsed + scene_elapsed
        total_cost = cartoon_result.cost_estimate + result.cost_estimate

        response = requests.get(result.image_url, timeout=120)
        response.raise_for_status()
        generated_img = Image.open(BytesIO(response.content))
        generated_path = str(order_dir / "generated.png")
        generated_img.save(generated_path, quality=95)

        step_data = {
            "pipeline": "cartoonify_then_kontext",
            "backend": backend,
            "cartoonify_model": cartoon_result.model_id,
            "scene_model": result.model_id,
            "prompt": prompt,
            "cartoonify_elapsed": round(cartoon_elapsed, 1),
            "scene_elapsed": round(scene_elapsed, 1),
            "elapsed_seconds": round(elapsed, 1),
            "cartoonify_cost": cartoon_result.cost_estimate,
            "scene_cost": result.cost_estimate,
            "cost_estimate": total_cost,
            "generated_size": list(generated_img.size),
            "status": "ok",
        }
        print(f"  Generated {generated_img.size[0]}x{generated_img.size[1]} in {elapsed:.1f}s (${total_cost})")

    else:
        # Single-step pipeline
        start = time.time()
        result = be.generate(
            prompt=prompt,
            image_path=image_path,
            style_settings={},
            negative_prompt=style_config.get("negative_prompt"),
            seed=seed,
        )
        elapsed = time.time() - start
        total_cost = result.cost_estimate

        response = requests.get(result.image_url, timeout=120)
        response.raise_for_status()
        generated_img = Image.open(BytesIO(response.content))
        generated_path = str(order_dir / "generated.png")
        generated_img.save(generated_path, quality=95)

        step_data = {
            "backend": backend,
            "model_id": result.model_id,
            "prompt": prompt,
            "elapsed_seconds": round(elapsed, 1),
            "cost_estimate": result.cost_estimate,
            "generated_size": list(generated_img.size),
            "status": "ok",
        }
        print(f"  Generated {generated_img.size[0]}x{generated_img.size[1]} in {elapsed:.1f}s (${result.cost_estimate})")

    return generated_path, total_cost, step_data


def fulfill_order(
    photo_path: str,
    style: str,
    subject: str,
    puzzle_size: int,
    order_id: str,
    backend: str = "flux_kontext",
    skip_consent: bool = False,
    face_swap: bool = True,
    gender: Optional[str] = None,
    seed: Optional[int] = None,
    max_attempts: int = 1,
    progress_callback: Optional[Callable] = None,
):
    """Full order fulfillment pipeline.

    Steps:
    1. Validate photo
    2. Log consent
    3. AI transform (with optional retry loop)
    4. Face swap (if enabled)
    5. Puzzle quality scoring + heatmap
    6. Upscale to print resolution (skipped on HARD_FAIL)
    7. Generate preview + print-ready

    Args:
        max_attempts: Max generation attempts. 1 = no retry (CLI default).
            Set higher for web UI. Disabled in LIGHTWEIGHT_MODE.
    """
    total_steps = 7

    def _progress(step: int, label: str):
        if progress_callback:
            progress_callback(step, label, total_steps)

    order_dir = Path("orders") / order_id
    order_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "order_id": order_id,
        "started_at": datetime.now().isoformat(),
        "photo_path": photo_path,
        "style": style,
        "subject": subject,
        "puzzle_size": puzzle_size,
        "backend": backend,
        "face_swap": face_swap,
        "gender": gender,
        "max_attempts": max_attempts,
        "steps": {},
    }

    print(f"Order: {order_id}")
    print(f"  Photo: {photo_path}")
    print(f"  Style: {style}, Backend: {backend}")
    if face_swap:
        print(f"  Face swap: enabled (gender={gender})")
    print(f"  Subject: {subject}")
    print(f"  Puzzle: {puzzle_size} pieces")
    if max_attempts > 1:
        print(f"  Max attempts: {max_attempts}")
    print()

    # Step 1: Validate photo
    _progress(1, "Validating photo")
    print("[1/7] Validating photo...")
    img = ImageOps.exif_transpose(Image.open(photo_path))
    w, h = img.size
    if w < 256 or h < 256:
        print(f"  Photo too small ({w}x{h}). Minimum 256x256.")
        sys.exit(1)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    manifest["steps"]["validate"] = {"size": (w, h), "mode": img.mode, "status": "ok"}
    print(f"  OK: {w}x{h} {img.mode}")

    # Step 2: Consent
    _progress(2, "Logging consent")
    if not skip_consent:
        print("[2/7] Logging consent...")
        from consent import log_consent
        consent = log_consent(
            order_id=order_id,
            photo_path=photo_path,
            consent_given=True,
            consent_method="etsy_message",
        )
        manifest["steps"]["consent"] = consent
        print("  Consent logged.")
    else:
        manifest["steps"]["consent"] = {"skipped": True}
        print("[2/7] Consent skipped (--skip-consent)")

    # Prepare input image
    temp_input = str(order_dir / "input_prepared.png")
    img_prepared = ImageOps.exif_transpose(Image.open(photo_path))
    if img_prepared.mode != "RGB":
        img_prepared = img_prepared.convert("RGB")
    img_prepared.save(temp_input)

    # Step 3: AI transform (with retry loop)
    _progress(3, "AI transform")
    from backends.registry import get_backend
    from style_presets import get_style

    be = get_backend(backend)
    style_config = get_style(style)

    # Check style face swap setting
    style_face_swap = style_config.get("face_swap", True)
    if face_swap and not style_face_swap:
        print("  Face swap disabled for this style")
        face_swap = False

    pipeline = style_config.get("pipeline", "kontext")
    base_prompt = style_config["kontext_prompt"].format(subject=subject)

    # Retry loop — disabled in LIGHTWEIGHT_MODE
    effective_attempts = 1 if LIGHTWEIGHT_MODE else max_attempts
    current_prompt = base_prompt
    current_seed = seed
    best_score = None
    best_generated_path = None
    best_transform_data = None
    total_cost = 0
    attempts_data = []

    for attempt in range(effective_attempts):
        if attempt > 0:
            print(f"\n  Retry attempt {attempt + 1}/{effective_attempts}...")
            _progress(3, f"Retry {attempt + 1}/{effective_attempts}")
            # Use different seed for retry
            current_seed = random.randint(1, 999999)

        print(f"[3/7] AI transform ({backend}, {style})...")
        generated_path, attempt_cost, transform_data = _generate_image(
            be, current_prompt, temp_input, style_config, backend,
            current_seed, order_dir, pipeline, progress_callback, total_steps,
        )
        total_cost += attempt_cost

        # Quick puzzle score check for retry decisions
        if effective_attempts > 1 or not LIGHTWEIGHT_MODE:
            from quality.puzzle_scorer import score_puzzle_quality, PuzzleGrade
            puzzle_check = score_puzzle_quality(generated_path, puzzle_size)
            attempt_info = {
                "attempt": attempt + 1,
                "prompt": current_prompt,
                "seed": current_seed,
                "cost": attempt_cost,
                "puzzle_composite": puzzle_check.composite,
                "puzzle_grade": puzzle_check.grade.value,
            }
            attempts_data.append(attempt_info)
            print(f"  Puzzle quality: {puzzle_check.composite}/100 ({puzzle_check.grade.value})")

            if puzzle_check.grade == PuzzleGrade.PASS:
                best_score = puzzle_check
                best_generated_path = generated_path
                best_transform_data = transform_data
                break  # Good enough, stop retrying

            # Track best attempt
            if best_score is None or puzzle_check.composite > best_score.composite:
                best_score = puzzle_check
                best_generated_path = generated_path
                best_transform_data = transform_data

            # Build retry prompt if more attempts remain
            if attempt < effective_attempts - 1:
                from retry_strategy import build_retry_prompt
                current_prompt = build_retry_prompt(base_prompt, puzzle_check)
        else:
            best_generated_path = generated_path
            best_transform_data = transform_data
            break

    # Use best attempt
    generated_path = best_generated_path
    manifest["steps"]["ai_transform"] = best_transform_data
    if attempts_data:
        manifest["steps"]["ai_transform"]["attempts"] = attempts_data

    # Step 4: Face swap (post-processing)
    _progress(4, "Face swap")
    if face_swap:
        print("[4/7] Face swap (codeplugtech)...")
        try:
            from backends.easel_swap import face_swap as run_face_swap
            import requests
            from io import BytesIO

            start = time.time()
            swap_result = run_face_swap(
                swap_image_path=temp_input,
                target_image_path=generated_path,
                gender=gender,
                hair_source="swap",
            )
            swap_elapsed = time.time() - start

            if swap_result.image_url is None:
                raise RuntimeError("Face swap returned no image URL")

            response = requests.get(swap_result.image_url, timeout=120)
            response.raise_for_status()
            swapped_img = Image.open(BytesIO(response.content))
            swapped_img.save(generated_path, quality=95)

            total_cost += swap_result.cost_estimate
            manifest["steps"]["face_swap"] = {
                "model_id": swap_result.model_id,
                "hair_source": "swap",
                "gender": gender,
                "elapsed_seconds": round(swap_elapsed, 1),
                "cost_estimate": swap_result.cost_estimate,
                "swapped_size": list(swapped_img.size),
                "status": "ok",
            }
            print(f"  Swapped in {swap_elapsed:.1f}s (${swap_result.cost_estimate})")
        except Exception as e:
            print(f"  WARNING: Face swap failed ({e}). Continuing with un-swapped image.")
            manifest["steps"]["face_swap"] = {"status": "failed", "error": str(e)}

    # Step 5: Quality scoring + heatmap
    _progress(5, "Quality scoring")
    if LIGHTWEIGHT_MODE:
        print("[5/7] Quality scoring... SKIPPED (lightweight mode)")
        # Still run puzzle scorer — it's lightweight (numpy+cv2 only)
        from quality.puzzle_scorer import score_puzzle_quality
        puzzle_result = score_puzzle_quality(generated_path, puzzle_size)
        quality = {
            "puzzle_composite": puzzle_result.composite,
            "puzzle_grade": puzzle_result.grade.value,
            "puzzle_pass": puzzle_result.grade.value == "PASS",
            "hard_fail_reasons": puzzle_result.hard_fail_reasons,
            "per_metric": {
                name: {
                    "raw": m.raw_value,
                    "score": m.normalized_score,
                    "weight": m.weight,
                    "hard_fail": m.hard_fail,
                }
                for name, m in puzzle_result.per_metric.items()
            },
            "face_similarity_raw": None,
            "lightweight": True,
        }
        print(f"  Puzzle quality: {puzzle_result.composite}/100 ({puzzle_result.grade.value})")
    else:
        print("[5/7] Quality scoring (puzzle + face)...")
        from quality import assess_full_quality
        quality = assess_full_quality(
            generated_path=generated_path,
            source_path=photo_path,
            puzzle_pieces=puzzle_size,
            save_thumbnails_dir=str(order_dir / "faces"),
        )
        # Convert PuzzleScore to serializable dict
        puzzle_result = quality.pop("puzzle_score")
        print(f"  Puzzle quality: {quality['puzzle_composite']}/100 ({quality['puzzle_grade']})")
        if quality.get("face_similarity_raw") is not None:
            print(f"  Face similarity: {quality['face_similarity_raw']:.4f}")
        for name, m_data in quality["per_metric"].items():
            flag = " *** HARD FAIL ***" if m_data.get("hard_fail") else ""
            print(f"    {name}: {m_data['score']}/100 (raw: {m_data['raw']}){flag}")
    manifest["steps"]["quality"] = quality

    # Generate heatmap
    print("  Generating puzzle heatmap...")
    from quality.heatmap import generate_heatmap
    heatmap_path = str(order_dir / "heatmap.png")
    heatmap_result = generate_heatmap(generated_path, heatmap_path)
    manifest["steps"]["heatmap"] = heatmap_result
    if heatmap_result.get("problem_regions"):
        n_problems = len(heatmap_result["problem_regions"])
        print(f"  Heatmap: {n_problems} problem region(s) found")
    else:
        print("  Heatmap: no problem regions")

    # Quality gate — check for hard fail before expensive upscale
    is_hard_fail = quality.get("puzzle_grade") == "HARD_FAIL" or quality.get("hard_fail_reasons")
    if is_hard_fail and not LIGHTWEIGHT_MODE:
        print(f"\n  *** QUALITY REJECTED — hard fail detected ***")
        for reason in quality.get("hard_fail_reasons", []):
            print(f"    - {reason}")
        print(f"  Skipping upscale + export (saves $0.002)")
        manifest["steps"]["quality"]["status"] = "quality_rejected"
        manifest["completed_at"] = datetime.now().isoformat()
        manifest["total_cost_estimate"] = total_cost
        manifest_path = order_dir / "manifest.json"
        with manifest_path.open("w") as f:
            json.dump(manifest, f, indent=2, default=str)
        print(f"\nOrder rejected. Files in {order_dir}/")
        print(f"  Generated image saved for inspection: {generated_path}")
        print(f"  Heatmap: {heatmap_path}")
        print(f"  Cost: ~${total_cost:.3f}")
        return manifest

    # Step 6: Upscale (skipped in lightweight mode)
    _progress(6, "Upscaling")
    upscale_cost = 0
    if LIGHTWEIGHT_MODE:
        print("[6/7] Upscaling... SKIPPED (lightweight mode)")
        upscaled_path = generated_path
        manifest["steps"]["upscale"] = {"skipped": True}
    else:
        print(f"[6/7] Upscaling to print resolution ({puzzle_size}pc)...")
        from upscale import upscale_for_print
        upscaled_path = str(order_dir / "upscaled.png")
        upscale_result = upscale_for_print(
            input_path=generated_path,
            output_path=upscaled_path,
            puzzle_pieces=puzzle_size,
        )
        manifest["steps"]["upscale"] = upscale_result
        upscale_cost = upscale_result.get("cost_estimate", 0)
        print(f"  Upscaled to {upscale_result['final_size'][0]}x{upscale_result['final_size'][1]}")

    # Step 7: Export preview + print-ready
    _progress(7, "Exporting")
    if LIGHTWEIGHT_MODE:
        print("[7/7] Exporting preview (lightweight mode)...")
        preview_path = str(order_dir / "preview.jpg")
        Image.open(generated_path).convert("RGB").save(preview_path, quality=90)
        manifest["steps"]["export"] = {"lightweight": True}
        print(f"  Preview: {preview_path}")
    else:
        print("[7/7] Generating preview and print-ready files...")
        from export import export_preview, export_print_ready

        preview_path = str(order_dir / "preview.jpg")
        export_preview(
            image_path=upscaled_path,
            output_path=preview_path,
            puzzle_pieces=puzzle_size,
        )
        print(f"  Preview: {preview_path}")

        print_path = str(order_dir / "print_ready.jpg")
        print_result = export_print_ready(
            image_path=upscaled_path,
            output_path=print_path,
            puzzle_pieces=puzzle_size,
        )
        manifest["steps"]["export"] = print_result
        print(f"  Print-ready: {print_path} ({print_result['dimensions'][0]}x{print_result['dimensions'][1]}, {print_result['dpi']}DPI, {print_result['file_size_mb']}MB)")

    # Save manifest
    manifest["completed_at"] = datetime.now().isoformat()
    manifest["total_cost_estimate"] = total_cost + upscale_cost
    manifest_path = order_dir / "manifest.json"
    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"\nOrder complete! Files in {order_dir}/")
    print(f"  Manifest: {manifest_path}")
    print(f"  Cost: ~${manifest['total_cost_estimate']:.3f}")

    return manifest


def parse_args():
    parser = argparse.ArgumentParser(description="Fulfill a puzzle order end-to-end.")
    parser.add_argument("--photo", required=True, help="Path to customer's photo")
    parser.add_argument("--style", default="animation_village")
    parser.add_argument("--subject", default="a smiling person",
                        help="Description of the person in the photo (include hair details for best results)")
    parser.add_argument("--puzzle-size", type=int, default=1000, choices=[500, 1000])
    parser.add_argument("--order-id", required=True, help="Order ID (e.g., ETSY-12345)")
    parser.add_argument("--backend", default="flux_kontext",
                        help="AI backend to use")
    parser.add_argument("--skip-consent", action="store_true",
                        help="Skip consent logging (for testing)")
    parser.add_argument("--no-face-swap", action="store_true",
                        help="Disable face swap post-processing (enabled by default)")
    parser.add_argument("--gender", default=None, choices=["male", "female", "non-binary"],
                        help="Gender for face swap metadata")
    parser.add_argument("--seed", type=int, default=None,
                        help="Fixed seed for reproducible results (omit for random)")
    parser.add_argument("--max-attempts", type=int, default=1,
                        help="Max generation attempts with auto-retry (default 1, set 3 for quality)")
    args = parser.parse_args()
    args.face_swap = not args.no_face_swap
    return args


if __name__ == "__main__":
    args = parse_args()
    fulfill_order(
        photo_path=args.photo,
        style=args.style,
        subject=args.subject,
        puzzle_size=args.puzzle_size,
        order_id=args.order_id,
        backend=args.backend,
        skip_consent=args.skip_consent,
        face_swap=args.face_swap,
        gender=args.gender,
        seed=args.seed,
        max_attempts=args.max_attempts,
    )
