"""A/B test: subject text injection vs no-subject-text character generation.

Tests Becca's hypothesis: does letting the AI model use the image to make
decisions (no text) preserve likeness better than injecting detected
attributes as text in the character prompt?

For each photo:
  1. Run bg removal once (shared).
  2. Call detect_attributes (Claude vision) to get age/gender/ethnicity/hair/skin.
  3. Build the main-style subject description via subject_builder.
  4. Run step_generate_character TWICE with the same seed:
       - Variant WITH_TEXT: subject=<built>, gender=<detected>
       - Variant NO_TEXT:   subject="the person in the input image", gender="person"
  5. Build a 3-panel comparison image [ORIGINAL | WITH_TEXT | NO_TEXT] with
     the subject text annotated so we know what each variant was told.

Cost: $0.17 per photo (bg + 2 × character).

Usage:
    .venv/bin/python3 scripts/ab_subject_text.py

Outputs: orders/AB-SUBJECT-TEXT/<photo>/
    original.png
    bg_removed.jpg
    character_input.png     (cropped face sent to model)
    with_text.png           (variant A — subject text injected)
    no_text.png             (variant B — "the person in the input image")
    comparison.png          (3-panel with labels and prompt text)
    metadata.json           (detected attrs, built subject, seeds)
"""

import json
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Fixed per-photo seeds so the run is reproducible but each photo is its own
# fair comparison (same seed for both variants within a photo).
# Original run covered all three; only charlie-outside needed a re-run after
# the detect_attributes 5 MB gate was added. Uncomment joel/lucy to re-run.
PHOTOS = [
    # ("joel-pub",         "input/joel/joel-pub.jpg",          42),
    # ("lucy-coffee",      "input/lucy/lucy-coffee.jpg",       42),
    ("charlie-outside",  "input/Chaz/charlie-outside.jpg",   42),
]
OUT_ROOT = Path("orders/AB-SUBJECT-TEXT")
SCENE = "village"


class DetectionFailed(RuntimeError):
    """Raised when detect_attributes returns empty data.

    We fail loud rather than falling through to defaults: an A/B test with a
    degraded subject description (e.g. 'a adult person, olive skin' because
    Claude didn't return anything) doesn't actually test the hypothesis — it
    compares two variants that are nearly identical, wasting money on a
    useless comparison. Better to stop and fix the detection.
    """


def _detect_attributes_strict(image_path: str) -> dict:
    """Call detect_attributes. Raise DetectionFailed on empty or error.

    detect_attributes itself handles resizing oversized images internally
    (see src/detect_attributes._prepare_image_payload). Any remaining empty
    response is a real failure — missing API key, network error, Claude
    refused to parse, etc. — and we stop the test rather than fabricate a
    fake subject.
    """
    from detect_attributes import detect_attributes
    result = detect_attributes(image_path)
    if not result:
        raise DetectionFailed(
            f"detect_attributes returned empty for {image_path}. "
            "Check ANTHROPIC_API_KEY is set and the image is a valid portrait."
        )
    expected = {"age_range", "gender", "ethnicity", "hair_color", "hair_style", "skin_tone"}
    missing = [k for k in expected if not result.get(k)]
    if missing:
        raise DetectionFailed(
            f"detect_attributes returned incomplete attributes for {image_path}. "
            f"Missing or empty: {missing}. Full response: {result}"
        )
    return result


def _build_subject(attrs: dict) -> tuple[str, str]:
    """Build the historical main-style subject description from detected attrs.

    This inlines the logic that used to live in src/subject_builder.py
    (deleted after the NO-TEXT A/B proved subject_builder harmful). Kept
    here as a frozen historical control so the A/B test can still replay
    the pre-merge behaviour.

    Returns (subject_text, gender_for_prompt).
    """
    age_range = attrs.get("age_range", "") or "adult"
    gender = attrs.get("gender", "") or "person"
    ethnicity = attrs.get("ethnicity", "") or ""
    hair_color = attrs.get("hair_color", "") or ""
    hair_style = attrs.get("hair_style", "") or ""
    skin_tone = attrs.get("skin_tone", "") or ""

    # Original build_subject_description format:
    # "a {age} {ethnicity?} {gender}, {skin} skin, {style} {color} hair"
    base = f"a {age_range}"
    if ethnicity:
        base += f" {ethnicity}"
    base += f" {gender}"
    parts = [base]
    if skin_tone:
        parts.append(f"{skin_tone} skin")
    hair_parts = [p for p in (hair_style, hair_color) if p]
    if hair_parts:
        parts.append(f"{' '.join(hair_parts)} hair")
    subject = ", ".join(parts)
    return subject or "a smiling person", gender


def _run_variant(
    bg_removed_path: str,
    subject: str,
    gender: str,
    seed: int,
    order_dir: Path,
    variant_name: str,
) -> dict:
    """Run step_generate_character for one variant and save output as <variant_name>.png."""
    from pipeline_steps import step_generate_character

    # Use a temp subdir so character_input.png and character.png don't collide
    variant_dir = order_dir / variant_name
    variant_dir.mkdir(parents=True, exist_ok=True)

    start = time.time()
    result = step_generate_character(
        bg_removed_path=bg_removed_path,
        subject=subject,
        gender=gender,
        scene=SCENE,
        order_dir=str(variant_dir),
        seed=seed,
    )
    elapsed = time.time() - start

    # Copy generated character.png up with the variant name for easy comparison
    src = variant_dir / "character.png"
    dst = order_dir / f"{variant_name}.png"
    if src.exists():
        Image.open(src).save(dst)

    print(f"    {variant_name}: {elapsed:.1f}s, ${result['cost']:.3f}")
    return {
        "variant": variant_name,
        "subject": subject,
        "gender": gender,
        "seed": seed,
        "cost": result["cost"],
        "elapsed": round(elapsed, 1),
        "character": str(dst),
    }


def _wrap_text(text: str, width: int) -> list:
    """Crude word-wrap for label text."""
    words = text.split()
    lines = []
    current = ""
    for w in words:
        candidate = (current + " " + w).strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = w
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _build_comparison(
    photo_name: str,
    photo_dir: Path,
    with_text_subject: str,
    no_text_subject: str,
):
    """Build a 3-panel comparison with subject-text labels below each panel."""
    panels = [
        ("ORIGINAL",       photo_dir / "original.png",  ""),
        ("WITH-TEXT",      photo_dir / "with_text.png", with_text_subject),
        ("NO-TEXT",        photo_dir / "no_text.png",   no_text_subject),
    ]

    imgs = []
    target_h = 900
    for label, path, sub in panels:
        if not path.exists():
            print(f"  WARN: missing {path}")
            continue
        img = Image.open(path).convert("RGB")
        scale = target_h / img.height
        new_w = round(img.width * scale)
        img = img.resize((new_w, target_h), Image.LANCZOS)
        imgs.append((label, img, sub))

    if len(imgs) < 3:
        print("  WARN: skipping comparison — not all 3 panels present")
        return

    label_h = 44
    sub_h = 110
    pad = 24
    total_w = sum(img.width for _, img, _ in imgs) + pad * 4
    total_h = target_h + label_h + sub_h + pad * 2

    canvas = Image.new("RGB", (total_w, total_h), (24, 24, 28))
    draw = ImageDraw.Draw(canvas)
    try:
        font_label = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except Exception:
        font_label = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    x = pad
    for label, img, sub in imgs:
        canvas.paste(img, (x, pad + label_h))
        # Centred label
        bbox = draw.textbbox((0, 0), label, font=font_label)
        text_w = bbox[2] - bbox[0]
        draw.text(
            (x + (img.width - text_w) // 2, pad),
            label,
            fill=(255, 255, 255),
            font=font_label,
        )
        # Subject text wrapped below
        if sub:
            lines = _wrap_text(f'subject="{sub}"', width=48)
            line_y = pad + label_h + target_h + 10
            for line in lines[:4]:
                draw.text((x + 8, line_y), line, fill=(200, 200, 210), font=font_sub)
                line_y += 22
        x += img.width + pad

    out_path = photo_dir / "comparison.png"
    canvas.save(out_path)
    print(f"  comparison -> {out_path}")


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    total_cost = 0.0
    summary = []

    from pipeline_steps import step_remove_background

    for photo_name, photo_path, seed in PHOTOS:
        if not Path(photo_path).exists():
            print(f"SKIP {photo_name}: {photo_path} not found")
            continue

        print(f"\n=== {photo_name} ({photo_path}) ===")
        photo_dir = OUT_ROOT / photo_name
        photo_dir.mkdir(parents=True, exist_ok=True)

        # 0. Copy original for comparison panel
        Image.open(photo_path).convert("RGB").save(photo_dir / "original.png")

        # 1. Run bg removal once (shared between variants)
        print("  step 1: bg removal")
        bg_path = str(photo_dir / "bg_removed.jpg")
        bg_result = step_remove_background(photo_path, str(photo_dir))
        # step_remove_background puts output in a specific place — normalise it
        bg_path = bg_result["bg_removed"]
        total_cost += bg_result["cost"]

        # 2. Detect attributes — FAIL LOUD if empty/incomplete.
        # A degraded subject description makes the A/B comparison meaningless,
        # so we refuse to spend money on character gens with bad data.
        print("  step 2: detect attributes")
        try:
            attrs = _detect_attributes_strict(photo_path)
        except DetectionFailed as e:
            print(f"  SKIP {photo_name}: {e}")
            continue
        attrs["_image_path"] = photo_path
        print(f"    attrs: {json.dumps({k: v for k, v in attrs.items() if not k.startswith('_')})}")

        # 3. Build subject description (main-style)
        subject_with_text, gender_with_text = _build_subject(attrs)
        subject_no_text, gender_no_text = "the person in the input image", "person"
        print(f"    WITH_TEXT subject: {subject_with_text!r}, gender: {gender_with_text!r}")
        print(f"    NO_TEXT   subject: {subject_no_text!r}, gender: {gender_no_text!r}")

        # 4. Run character gen twice with same seed
        print("  step 3: character generation (2 variants)")
        with_text = _run_variant(bg_path, subject_with_text, gender_with_text, seed, photo_dir, "with_text")
        total_cost += with_text["cost"]
        no_text = _run_variant(bg_path, subject_no_text, gender_no_text, seed, photo_dir, "no_text")
        total_cost += no_text["cost"]

        # 5. Save metadata
        metadata = {
            "photo": photo_path,
            "seed": seed,
            "detected_attributes": {k: v for k, v in attrs.items() if not k.startswith("_")},
            "variants": {
                "with_text": {"subject": subject_with_text, "gender": gender_with_text},
                "no_text":   {"subject": subject_no_text,   "gender": gender_no_text},
            },
        }
        (photo_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

        # 6. Build comparison image
        _build_comparison(photo_name, photo_dir, subject_with_text, subject_no_text)
        summary.append((photo_name, photo_dir / "comparison.png", subject_with_text))

    print(f"\n=== DONE ===")
    print(f"Total cost: ${total_cost:.3f}")
    print("\nComparisons:")
    for name, path, subj in summary:
        print(f"  {name}: {path}")
        print(f"    WITH_TEXT subject was: {subj}")


if __name__ == "__main__":
    main()
