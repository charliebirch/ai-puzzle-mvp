"""
Order fulfillment CLI - single command to process a customer order end-to-end.

Usage:
    python src/fulfill_order.py --photo customer.jpg --style fairytale \
        --subject "a young girl" --puzzle-size 1000 --order-id ETSY-12345

    python src/fulfill_order.py --photo customer.jpg --style storybook_cartoon \
        --subject "a young man" --puzzle-size 500 --order-id ETSY-67890 --skip-consent
"""

import argparse
import json
import os
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
    progress_callback: Optional[Callable] = None,
):
    """Full order fulfillment pipeline.

    Steps:
    1. Validate photo
    2. Log consent
    3. AI transform (Kontext Pro) + face swap
    4. Quality score
    5. Upscale to print resolution
    6. Generate preview (with grid) and print-ready (with bleed)
    7. Save everything to orders/<order_id>/
    """
    total_steps = 7

    def _progress(step: int, label: str):
        """Report progress to callback if provided."""
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
        "steps": {},
    }

    print(f"Order: {order_id}")
    print(f"  Photo: {photo_path}")
    print(f"  Style: {style}, Backend: {backend}")
    if face_swap:
        print(f"  Face swap: enabled (gender={gender})")
    print(f"  Subject: {subject}")
    print(f"  Puzzle: {puzzle_size} pieces")
    print()

    # Step 1: Validate photo
    _progress(1, "Validating photo")
    print("[1/6] Validating photo...")
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
        print("[2/6] Logging consent...")
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
        print("[2/6] Consent skipped (--skip-consent)")

    # Step 3: AI transform
    _progress(3, "AI transform")
    from backends.registry import get_backend
    from style_presets import get_style

    be = get_backend(backend)
    style_config = get_style(style)

    # Check if this style disables face swap (e.g. pixel art styles)
    style_face_swap = style_config.get("face_swap", True)
    if face_swap and not style_face_swap:
        print("  Face swap disabled for this style (pixel art)")
        face_swap = False

    # Prepare input image
    temp_input = str(order_dir / "input_resized.jpg")
    img_resized = ImageOps.exif_transpose(Image.open(photo_path))
    if img_resized.mode != "RGB":
        img_resized = img_resized.convert("RGB")
    max_size = 1024
    if max(img_resized.size) > max_size:
        img_resized.thumbnail((max_size, max_size))
    img_resized.save(temp_input, quality=95)

    print(f"[3/6] AI transform ({backend}, {style})...")

    prompt = style_config["kontext_prompt"]

    start = time.time()
    result = be.generate(
        prompt=prompt,
        image_path=temp_input,
        style_settings=style_config["settings"],
        negative_prompt=style_config.get("negative_prompt"),
    )
    elapsed = time.time() - start
    total_cost = result.cost_estimate

    # Download generated image
    import requests
    from io import BytesIO
    response = requests.get(result.image_url, timeout=120)
    response.raise_for_status()
    generated_img = Image.open(BytesIO(response.content))
    generated_path = str(order_dir / "generated.png")
    generated_img.save(generated_path, quality=95)

    manifest["steps"]["ai_transform"] = {
        "backend": backend,
        "model_id": result.model_id,
        "prompt": prompt,
        "elapsed_seconds": round(elapsed, 1),
        "cost_estimate": result.cost_estimate,
        "generated_size": list(generated_img.size),
        "status": "ok",
    }
    print(f"  Generated {generated_img.size[0]}x{generated_img.size[1]} in {elapsed:.1f}s (${result.cost_estimate})")

    # Step 4: Face swap (post-processing)
    _progress(4, "Face swap")
    if face_swap:
        print("[3b/6] Face swap (codeplugtech)...")
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

            # Download swapped image and replace generated.png
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
            print(f"  Swapped {swapped_img.size[0]}x{swapped_img.size[1]} in {swap_elapsed:.1f}s (${swap_result.cost_estimate})")
        except Exception as e:
            print(f"  WARNING: Face swap failed ({e}). Continuing with un-swapped image.")
            manifest["steps"]["face_swap"] = {"status": "failed", "error": str(e)}

    # Step 5: Quality score (skipped in lightweight mode — needs InsightFace ~300MB)
    _progress(5, "Quality scoring")
    if LIGHTWEIGHT_MODE:
        print("[4/6] Quality scoring... SKIPPED (lightweight mode)")
        quality = {"composite_score": 0, "pass": False, "skipped": True}
    else:
        print("[4/6] Quality scoring...")
        from quality import assess_quality
        quality = assess_quality(
            generated_path=generated_path,
            source_path=photo_path,
            target_pieces=puzzle_size,
            save_thumbnails_dir=str(order_dir / "faces"),
        )
        print(f"  Composite: {quality['composite_score']}/100 ({'PASS' if quality['pass'] else 'FAIL'})")
        if quality.get("face_similarity_raw") is not None:
            print(f"  Face similarity: {quality['face_similarity_raw']:.4f} ({quality.get('face_confidence', 'n/a')})")
    manifest["steps"]["quality"] = quality

    # Step 6: Upscale (skipped in lightweight mode)
    _progress(6, "Upscaling")
    upscale_cost = 0
    if LIGHTWEIGHT_MODE:
        print(f"[5/6] Upscaling... SKIPPED (lightweight mode)")
        # Use generated image directly as preview
        upscaled_path = generated_path
        manifest["steps"]["upscale"] = {"skipped": True}
    else:
        print(f"[5/6] Upscaling to print resolution ({puzzle_size}pc)...")
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
        print("[6/6] Exporting preview (lightweight mode)...")
        # Just copy generated image as preview — no grid overlay or print-ready
        preview_path = str(order_dir / "preview.jpg")
        Image.open(generated_path).convert("RGB").save(preview_path, quality=90)
        manifest["steps"]["export"] = {"lightweight": True}
        print(f"  Preview: {preview_path}")
    else:
        print("[6/6] Generating preview and print-ready files...")
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
    parser.add_argument("--style", default="storybook_cartoon")
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
    )
