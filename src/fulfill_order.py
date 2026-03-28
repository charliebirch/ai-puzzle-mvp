"""
Order fulfillment CLI - generates a Pixar-style character from a customer photo.

Usage:
    python src/fulfill_order.py --photo customer.jpg --style village \
        --subject "a young girl with curly red hair" --order-id ETSY-12345

    python src/fulfill_order.py --photo customer.jpg --style space \
        --subject "a young man" --order-id ETSY-67890
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from dotenv import load_dotenv
from PIL import Image, ImageOps

load_dotenv()


def fulfill_order(
    photo_path: str,
    style: str,
    subject: str,
    order_id: str,
    backend: str = "flux_kontext",
    seed: Optional[int] = None,
    progress_callback: Optional[Callable] = None,
):
    """Generate a Pixar-style character from a customer photo.

    Steps:
    1. Validate photo
    2. AI character generation (single-step Kontext)
    3. Save preview

    Returns manifest dict with generation metadata.
    """
    total_steps = 3

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
        "backend": backend,
        "steps": {},
    }

    print(f"Order: {order_id}")
    print(f"  Photo: {photo_path}")
    print(f"  Style: {style}, Backend: {backend}")
    print(f"  Subject: {subject}")
    print()

    # Step 1: Validate photo
    _progress(1, "Validating photo")
    print("[1/3] Validating photo...")
    img = ImageOps.exif_transpose(Image.open(photo_path))
    w, h = img.size
    if w < 256 or h < 256:
        print(f"  Photo too small ({w}x{h}). Minimum 256x256.")
        sys.exit(1)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    manifest["steps"]["validate"] = {"size": (w, h), "mode": img.mode, "status": "ok"}
    print(f"  OK: {w}x{h} {img.mode}")

    # Prepare input image
    temp_input = str(order_dir / "input_prepared.png")
    img_prepared = ImageOps.exif_transpose(Image.open(photo_path))
    if img_prepared.mode != "RGB":
        img_prepared = img_prepared.convert("RGB")
    img_prepared.save(temp_input)

    # Step 2: AI character generation
    _progress(2, "Generating character")
    print(f"[2/3] Generating character ({backend}, {style})...")

    import requests
    from io import BytesIO
    from backends.registry import get_backend
    from style_presets import get_style

    be = get_backend(backend)
    style_config = get_style(style)
    prompt = style_config["kontext_prompt"].format(subject=subject)

    start = time.time()
    result = be.generate(
        prompt=prompt,
        image_path=temp_input,
        style_settings={},
        negative_prompt=style_config.get("negative_prompt"),
        seed=seed,
    )
    elapsed = time.time() - start

    response = requests.get(result.image_url, timeout=120)
    response.raise_for_status()
    generated_img = Image.open(BytesIO(response.content))
    generated_path = str(order_dir / "generated.png")
    generated_img.save(generated_path, quality=95)

    manifest["steps"]["generate"] = {
        "backend": backend,
        "model_id": result.model_id,
        "prompt": prompt,
        "elapsed_seconds": round(elapsed, 1),
        "cost_estimate": result.cost_estimate,
        "generated_size": list(generated_img.size),
        "status": "ok",
    }
    print(f"  Generated {generated_img.size[0]}x{generated_img.size[1]} in {elapsed:.1f}s (${result.cost_estimate})")

    # Step 3: Save preview
    _progress(3, "Saving preview")
    print("[3/3] Saving preview...")
    preview_path = str(order_dir / "preview.jpg")
    generated_img.convert("RGB").save(preview_path, quality=90)
    print(f"  Preview: {preview_path}")

    # Save manifest
    manifest["completed_at"] = datetime.now().isoformat()
    manifest["total_cost_estimate"] = result.cost_estimate
    manifest_path = order_dir / "manifest.json"
    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"\nOrder complete! Files in {order_dir}/")
    print(f"  Manifest: {manifest_path}")
    print(f"  Cost: ~${manifest['total_cost_estimate']:.3f}")

    return manifest


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a Pixar-style character from a photo.")
    parser.add_argument("--photo", required=True, help="Path to customer's photo")
    parser.add_argument("--style", default="village", choices=["village", "space", "underwater"])
    parser.add_argument("--subject", default="a smiling person",
                        help="Description of the person (e.g. 'a young boy with curly red hair')")
    parser.add_argument("--order-id", required=True, help="Order ID (e.g., ETSY-12345)")
    parser.add_argument("--backend", default="flux_kontext",
                        help="AI backend (flux_kontext or flux_kontext_max)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Fixed seed for reproducible results")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    fulfill_order(
        photo_path=args.photo,
        style=args.style,
        subject=args.subject,
        order_id=args.order_id,
        backend=args.backend,
        seed=args.seed,
    )
