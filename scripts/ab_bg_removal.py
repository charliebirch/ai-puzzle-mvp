"""A/B test: recraft vs lucataco background removal.

Runs both backends on the same set of photos and builds side-by-side
comparison images so the outputs can be judged visually.

Usage:
    .venv/bin/python3 scripts/ab_bg_removal.py

Outputs: orders/AB-RECRAFT-VS-LUCATACO/<photo>/
  - original.png
  - lucataco.png
  - recraft.png
  - comparison.png  (original | lucataco | recraft, side-by-side)
"""

import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

PHOTOS = [
    ("joel-pub", "input/joel/joel-pub.jpg"),
    ("lucy-coffee", "input/lucy/lucy-coffee.jpg"),
    ("charlie-outside", "input/Chaz/charlie-outside.jpg"),
]
OUT_ROOT = Path("orders/AB-RECRAFT-VS-LUCATACO")
BACKENDS = ["lucataco", "recraft"]


def run_backend(backend: str, input_path: str, output_path: str) -> dict:
    """Run BG removal with a specific backend. Imports fresh so the env var
    is read at import time for each backend."""
    os.environ["BG_REMOVAL_BACKEND"] = backend
    # Force re-import so the module re-reads BG_REMOVAL_BACKEND
    if "remove_background" in sys.modules:
        del sys.modules["remove_background"]
    from remove_background import remove_background

    print(f"  -> {backend} ...", flush=True)
    start = time.time()
    result = remove_background(input_path, output_path)
    elapsed = time.time() - start
    print(f"     done in {elapsed:.1f}s, cost ${result['cost_estimate']:.3f}")
    return result


def build_comparison(photo_name: str, photo_dir: Path) -> Path:
    """Build a 3-panel comparison: original | lucataco | recraft.
    Resize all to equal height with preserved aspect, label each panel.
    """
    panels = [
        ("ORIGINAL", photo_dir / "original.png"),
        ("LUCATACO", photo_dir / "lucataco.png"),
        ("RECRAFT",  photo_dir / "recraft.png"),
    ]

    imgs = []
    target_h = 800
    for label, path in panels:
        img = Image.open(path).convert("RGB")
        scale = target_h / img.height
        new_w = round(img.width * scale)
        img = img.resize((new_w, target_h), Image.LANCZOS)
        imgs.append((label, img))

    label_h = 40
    pad = 20
    total_w = sum(img.width for _, img in imgs) + pad * 4
    total_h = target_h + label_h + pad * 2

    canvas = Image.new("RGB", (total_w, total_h), (30, 30, 30))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except Exception:
        font = ImageFont.load_default()

    x = pad
    for label, img in imgs:
        canvas.paste(img, (x, pad + label_h))
        # Centre label over the image
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text(
            (x + (img.width - text_w) // 2, pad),
            label,
            fill=(255, 255, 255),
            font=font,
        )
        x += img.width + pad

    out_path = photo_dir / "comparison.png"
    canvas.save(out_path)
    return out_path


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    total_cost = 0.0
    results = []
    for photo_name, photo_path in PHOTOS:
        if not Path(photo_path).exists():
            print(f"SKIP {photo_name}: {photo_path} not found")
            continue

        print(f"\n=== {photo_name} ({photo_path}) ===")
        photo_dir = OUT_ROOT / photo_name
        photo_dir.mkdir(parents=True, exist_ok=True)

        # Save a copy of the original as PNG for the comparison
        original_copy = photo_dir / "original.png"
        Image.open(photo_path).convert("RGB").save(original_copy)

        for backend in BACKENDS:
            out_path = photo_dir / f"{backend}.png"
            result = run_backend(backend, photo_path, str(out_path))
            total_cost += result["cost_estimate"]

        comparison = build_comparison(photo_name, photo_dir)
        print(f"  Comparison -> {comparison}")
        results.append((photo_name, comparison))

    print(f"\n=== DONE ===")
    print(f"Total cost: ${total_cost:.3f}")
    print(f"\nComparison images:")
    for name, path in results:
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
