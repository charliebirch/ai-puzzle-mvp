"""
Pipeline step functions for the 5-step puzzle generation workflow.

Each function handles one step, takes simple arguments (paths, strings),
and returns a result dict. No web framework dependencies.

Steps:
1. Validate & prepare photo
2. Remove background ($0.01)
3. Generate Pixar character ($0.08)
4. Add themed costume ($0.08)
5. Generate scene + 3 compositing methods ($0.32)

Total cost: ~$0.49 per full run.
"""

import json
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable, Optional

import requests
from PIL import Image, ImageOps
from dotenv import load_dotenv

load_dotenv()


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}

# Prodigi print specs: exact pixel dimensions at 300 DPI, sRGB, JPG
PRODIGI_SIZES = {
    "110pc": (2953, 2362),   # 250×200mm — 5:4 ratio
    "252pc": (4429, 3366),   # 375×285mm — ~4:3 ratio
}
TIN_LID_SIZE = (869, 674)    # Small tin lid (fits 30/110/252pc puzzles)


def step_validate_and_prepare(photo_path: str, order_dir: str) -> dict:
    """Step 1: Validate photo and prepare input image.

    Checks file type, converts HEIC if needed, EXIF-corrects, validates
    size, checks for face detection and blur, and saves as input_prepared.png.

    Args:
        photo_path: Path to the uploaded photo.
        order_dir: Path to the order output directory.

    Returns:
        dict with input_prepared path, size, warnings, and quality checks.

    Raises:
        ValueError: If file type is not supported or image is too small.
    """
    import subprocess
    import platform

    order_dir = Path(order_dir)
    order_dir.mkdir(parents=True, exist_ok=True)

    # Check file type
    ext = Path(photo_path).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Please upload a JPEG, PNG, or HEIC image."
        )

    # Convert HEIC to JPEG if needed (Pillow doesn't support HEIC natively)
    if ext in (".heic", ".heif"):
        if platform.system() == "Darwin":
            converted_path = str(Path(photo_path).with_suffix(".jpg"))
            subprocess.run(
                ["sips", "-s", "format", "jpeg", photo_path, "--out", converted_path],
                check=True, capture_output=True,
            )
            photo_path = converted_path
        else:
            raise ValueError(
                "HEIC files are not supported on this server. Please upload a JPEG or PNG."
            )

    img = ImageOps.exif_transpose(Image.open(photo_path))
    w, h = img.size

    warnings = []

    # Hard reject: too small
    if w < 256 or h < 256:
        raise ValueError(f"Photo too small ({w}x{h}). Minimum 256x256 required.")

    # Soft warning: small but usable
    if w < 512 or h < 512:
        warnings.append(f"Photo is small ({w}x{h}). 512x512 minimum recommended for best results.")

    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    elif img.mode == "RGBA":
        img = img.convert("RGB")

    output_path = str(order_dir / "input_prepared.png")
    img.save(output_path, quality=95)

    # --- Quality checks using OpenCV (non-blocking, skip if unavailable) ---
    try:
        import cv2

        cv_img = cv2.imread(output_path)
        if cv_img is not None:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

            # Face detection
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            face_cascade = cv2.CascadeClassifier(cascade_path)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

            if len(faces) == 0:
                warnings.append("No face detected. The AI works best with a clearly visible face.")
            elif len(faces) > 1:
                warnings.append(f"{len(faces)} faces detected. For best results, use a photo with one person only.")

            # Blur detection (Laplacian variance)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < 50:
                warnings.append(f"Photo appears blurry (sharpness: {laplacian_var:.0f}). A sharper photo will give better results.")
    except ImportError:
        pass  # OpenCV not available (e.g. Render lightweight mode)

    return {
        "input_prepared": output_path,
        "size": [w, h],
        "warnings": warnings,
        "cost": 0,
    }


def step_remove_background(input_prepared_path: str, order_dir: str) -> dict:
    """Step 2: Remove background and replace with white.

    Uses lucataco/remove-bg on Replicate (~$0.01).

    Args:
        input_prepared_path: Path to the prepared input photo.
        order_dir: Path to the order output directory.

    Returns:
        dict with bg_removed path, cost, and elapsed time.
    """
    from remove_background import remove_background

    output_path = str(Path(order_dir) / "bg_removed.jpg")
    start = time.time()
    result = remove_background(input_prepared_path, output_path)
    elapsed = time.time() - start

    return {
        "bg_removed": output_path,
        "cost": result["cost_estimate"],
        "elapsed_seconds": round(elapsed, 1),
        "size": result["size"],
    }


def _crop_to_face(bg_removed_path: str, output_path: str) -> str:
    """Crop a white-background cutout image to face + upper chest only.

    Finds the bounding box of non-white pixels (the person cutout), then takes
    the top portion of that box (roughly face + shoulders). This prevents Kontext
    Max from seeing hand positions, body poses, or anything below the chest in
    the source photo.

    Falls back to the original image if cropping fails (e.g. image is entirely
    white or very small).

    Args:
        bg_removed_path: Path to the white-background cutout (bg_removed.jpg).
        output_path: Where to save the cropped image (character_input.png).

    Returns:
        Path to the cropped image (output_path), or bg_removed_path on failure.
    """
    try:
        img = Image.open(bg_removed_path).convert("RGBA")
        w, h = img.size

        # Build a mask of non-white pixels (person silhouette)
        # White = R>240, G>240, B>240
        r, g, b, a = img.split()
        import array as _array
        pixels_r = list(r.getdata())
        pixels_g = list(g.getdata())
        pixels_b = list(b.getdata())

        # Find bounding box of non-white pixels
        min_x, min_y, max_x, max_y = w, h, 0, 0
        for idx, (pr, pg, pb) in enumerate(zip(pixels_r, pixels_g, pixels_b)):
            if pr < 240 or pg < 240 or pb < 240:
                px = idx % w
                py = idx // w
                min_x = min(min_x, px)
                max_x = max(max_x, px)
                min_y = min(min_y, py)
                max_y = max(max_y, py)

        if max_x <= min_x or max_y <= min_y:
            # No non-white pixels found — fall back
            return bg_removed_path

        person_h = max_y - min_y
        person_w = max_x - min_x

        # Take the top 45% of the person's height (face + upper chest)
        # with a horizontal padding of 20% of person width on each side
        crop_h = int(person_h * 0.45)
        pad_x  = int(person_w * 0.20)

        left   = max(0, min_x - pad_x)
        top    = max(0, min_y - int(person_h * 0.05))   # small top margin
        right  = min(w, max_x + pad_x)
        bottom = min(h, min_y + crop_h)

        if (right - left) < 64 or (bottom - top) < 64:
            return bg_removed_path

        cropped = img.crop((left, top, right, bottom)).convert("RGB")

        # Composite onto white background
        white = Image.new("RGB", cropped.size, (255, 255, 255))
        if cropped.mode == "RGBA":
            white.paste(cropped, mask=cropped.split()[3])
        else:
            white.paste(cropped)

        white.save(output_path)
        return output_path

    except Exception as e:
        print(f"  _crop_to_face: failed ({e}), using full bg_removed image")
        return bg_removed_path


def step_generate_character(
    bg_removed_path: str,
    subject: str,
    gender: str,
    scene: str,
    order_dir: str,
    seed: Optional[int] = None,
) -> dict:
    """Step 3: Generate Pixar-style character using Kontext Max.

    Transforms the white-background photo into a Pixar-like 3D animated
    character, preserving identity. Cost: ~$0.08.

    Args:
        bg_removed_path: Path to the background-removed photo.
        subject: Description of the person.
        gender: 'boy', 'girl', or 'person'.
        scene: Scene ID (e.g. 'village') for prompt selection.
        order_dir: Path to the order output directory.
        seed: Optional seed for reproducibility.

    Returns:
        dict with character path, cost, and elapsed time.
    """
    from backends.registry import get_backend
    from scene_prompts import get_character_prompt

    # Crop bg_removed down to face + upper chest so the model only sees
    # identity reference, not the source pose or hand positions.
    character_input_path = str(Path(order_dir) / "character_input.png")
    actual_input = _crop_to_face(bg_removed_path, character_input_path)
    used_crop = actual_input == character_input_path
    print(f"  Character input: {'cropped face' if used_crop else 'full bg_removed (crop failed)'}")

    prompt = get_character_prompt(scene, subject, gender)
    backend = get_backend("flux_kontext_max")

    start = time.time()
    result = backend.generate(
        prompt=prompt,
        image_path=actual_input,
        style_settings={},
        seed=seed,
    )
    elapsed = time.time() - start

    # Download and save
    response = requests.get(result.image_url, timeout=120)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content))
    output_path = str(Path(order_dir) / "character.png")
    img.save(output_path, quality=95)

    return {
        "character": output_path,
        "character_input": character_input_path if used_crop else None,
        "cost": result.cost_estimate,
        "elapsed_seconds": round(elapsed, 1),
        "size": list(img.size),
        "prompt": prompt,
    }


def step_costume(
    character_path: str,
    scene: str,
    order_dir: str,
    seed: Optional[int] = None,
    outfit_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict:
    """Step 4: Dress the character in a themed costume using Kontext Max.

    Keeps face, hair, expression identical — only changes clothing. Cost: ~$0.08.

    Args:
        character_path: Path to the character image (white background).
        scene: Scene ID for costume selection.
        order_dir: Path to the order output directory.
        seed: Optional seed for reproducibility.
        outfit_id: Optional outfit choice ID from scene outfit_choices. Falls back
            to the scene's default costume_prompt if not provided or not found.
        subject: Subject description (e.g. 'a young man with short dark hair').
            Substituted into the prompt as an explicit hair/identity anchor.
            Falls back to 'a person' if not provided.

    Returns:
        dict with costumed path, cost, and elapsed time.
    """
    from backends.registry import get_backend
    from scene_prompts import get_costume_prompt

    prompt = get_costume_prompt(
        scene_id=scene,
        subject=subject or "a person",
        outfit_id=outfit_id,
    )
    backend = get_backend("flux_kontext_max")

    start = time.time()
    result = backend.generate(
        prompt=prompt,
        image_path=character_path,
        style_settings={},
        seed=seed,
    )
    elapsed = time.time() - start

    # Download and save
    response = requests.get(result.image_url, timeout=120)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content))
    output_path = str(Path(order_dir) / "costumed.png")
    img.save(output_path, quality=95)

    return {
        "costumed": output_path,
        "cost": result.cost_estimate,
        "elapsed_seconds": round(elapsed, 1),
        "size": list(img.size),
    }


def step_composite(
    costumed_path: str,
    scene: str,
    order_dir: str,
    seed: Optional[int] = None,
    progress_callback: Optional[Callable] = None,
) -> dict:
    """Step 5: Generate scene, composite character, pick best, upscale.

    Generates a detailed scene via FLUX 2 Pro, then PIL-composites the
    costumed character onto it. Runs through Kontext Max 3 times with
    different seeds, quality-scores each, picks the best, and upscales
    with Real-ESRGAN.

    Sub-steps (3 total):
    1. Scene generation (FLUX 2 Pro text-only, $0.08)
    2. Compositing: 3 candidates with different seeds (Kontext Max x3, $0.24)
    3. Scoring candidates

    Upscaling happens separately after user picks their favourite.
    Total cost: ~$0.32 (compositing) + $0.002 (upscale after pick).

    Args:
        costumed_path: Path to the costumed character image.
        scene: Scene ID for prompt selection.
        order_dir: Path to the order output directory.
        seed: Optional seed for reproducibility.
        progress_callback: Optional callback(sub_step, label, sub_total) for progress updates.

    Returns:
        dict with scene path, final composite path, candidate scores, cost, and timing.
    """
    import random

    from backends.registry import get_backend
    from composite_pil import composite_character_onto_scene
    from scene_prompts import get_scene
    from upscale import upscale_image

    scene_config = get_scene(scene)
    order_dir = Path(order_dir)
    total_cost = 0
    total_elapsed = 0
    sub_total = 3

    def _progress(sub_step: int, label: str):
        if progress_callback:
            progress_callback(sub_step, label, sub_total)

    # --- Sub-step 1: Generate empty scene via FLUX 2 Pro (text-only) ---
    _progress(1, "Generating scene")
    scene_path = str(order_dir / "scene.png")

    import replicate as _replicate
    start = time.time()
    scene_inputs = {
        "prompt": scene_config["scene_prompt"],
        "resolution": "4 MP",
        "aspect_ratio": "4:3",  # Landscape — matches all Prodigi puzzle formats
        "output_format": "png",
        "output_quality": 100,
        "safety_tolerance": 5,
    }
    if seed is not None:
        scene_inputs["seed"] = seed
    scene_output = _replicate.run("black-forest-labs/flux-2-pro", input=scene_inputs)
    # Extract URL
    scene_url = scene_output
    if isinstance(scene_output, list):
        scene_url = scene_output[0]
    if hasattr(scene_url, "url"):
        scene_url = str(getattr(scene_url, "url"))
    scene_url = str(scene_url)
    scene_elapsed = time.time() - start

    response = requests.get(scene_url, timeout=120)
    response.raise_for_status()
    scene_img = Image.open(BytesIO(response.content))
    scene_img.save(scene_path, quality=95)
    scene_cost = 0.08
    total_cost += scene_cost
    total_elapsed += scene_elapsed
    print(f"  Scene generated in {scene_elapsed:.1f}s ({scene_img.size[0]}x{scene_img.size[1]})")

    # --- Sub-step 2: Generate 3 composite candidates with different seeds ---
    _progress(2, "Compositing character into scene (3 candidates)")
    backend = get_backend("flux_kontext_max")

    pil_composite_path = str(order_dir / "_pil_composite.png")
    composite_character_onto_scene(costumed_path, scene_path, pil_composite_path)

    # Generate 3 seeds with wide spread so each candidate is genuinely different.
    # Close seeds (e.g. +10, +20) tend to produce similar failure modes — a bad
    # blend pattern at seed N often repeats at N+10. Using large prime-spaced
    # offsets gives three independent rolls.
    if seed is not None:
        seeds = [seed, seed + 31337, seed + 77777]
    else:
        base = random.randint(1, 999999)
        seeds = [base, (base + 31337) % 1_000_000, (base + 77777) % 1_000_000]

    candidates = []
    for i, s in enumerate(seeds):
        candidate_path = str(order_dir / f"candidate_{i+1}.png")
        start = time.time()
        result = backend.generate(
            prompt=scene_config["composite_E_prompt"],
            image_path=pil_composite_path,
            style_settings={},
            aspect_ratio="4:3",  # Landscape — matches Prodigi puzzle format
            seed=s,
        )
        elapsed = time.time() - start

        response = requests.get(result.image_url, timeout=120)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        img.save(candidate_path, quality=95)

        total_cost += result.cost_estimate
        total_elapsed += elapsed
        candidates.append({
            "path": candidate_path,
            "seed": s,
            "size": list(img.size),
        })
        print(f"  Candidate {i+1}/3 generated (seed={s})")

    # --- Sub-step 3: Score candidates ---
    _progress(3, "Scoring candidates")

    try:
        from quality.puzzle_scorer import score_puzzle_quality

        for i, candidate in enumerate(candidates):
            score_result = score_puzzle_quality(candidate["path"])
            candidate["quality_score"] = score_result.composite
            candidate["quality_grade"] = score_result.grade.value
            print(f"  Candidate {i+1}: score={score_result.composite:.1f} ({score_result.grade.value})")
    except ImportError:
        print("  Quality scorer unavailable, skipping scoring")
        for candidate in candidates:
            candidate["quality_score"] = None
            candidate["quality_grade"] = "N/A"

    # Clean up temp files
    Path(pil_composite_path).unlink(missing_ok=True)

    # Return candidates for user to pick — upscale happens after selection
    return {
        "scene": scene_path,
        "candidates": [c["path"] for c in candidates],
        "scores": {
            f"candidate_{i+1}": {
                "score": c["quality_score"],
                "grade": c["quality_grade"],
                "seed": c["seed"],
            }
            for i, c in enumerate(candidates)
        },
        "cost": round(total_cost, 3),
        "elapsed_seconds": round(total_elapsed, 1),
        "scene_size": list(scene_img.size),
    }


def step_upscale_final(candidate_path: str, order_dir: str) -> dict:
    """Upscale the user's chosen candidate to final resolution.

    Called after the user picks their favourite from the 3 candidates.
    Uses Real-ESRGAN 2x (anime model preferred, general fallback).

    Args:
        candidate_path: Path to the chosen candidate image.
        order_dir: Path to the order output directory.

    Returns:
        dict with final path, cost, and size.
    """
    from upscale import upscale_image

    final_path = str(Path(order_dir) / "final.png")
    result = upscale_image(
        input_path=candidate_path,
        output_path=final_path,
        scale=4,  # 4x needed for 300 DPI print (110pc=2953px, 252pc=4429px)
        anime=False,  # anime model (xinntao) currently broken on Replicate
        face_enhance=False,
    )
    final_size = list(result.get("final_size", result.get("upscaled_size", (0, 0))))
    print(f"  Upscaled to {final_size[0]}x{final_size[1]}")

    return {
        "final": final_path,
        "final_size": final_size,
        "cost": result["cost_estimate"],
    }


def step_export_for_print(upscaled_path: str, size_code: str, order_dir: str) -> dict:
    """Export print-ready files for Prodigi fulfillment.

    Produces puzzle_surface.jpg at the exact Prodigi pixel dimensions for the
    given size code, and tin_lid.jpg (center-cropped from the surface) in order_dir.

    Resize strategy: scale-to-fill then center-crop. This matches Prodigi's own
    fillPrintArea behaviour, so the preview is an accurate representation of print.

    Args:
        upscaled_path: Path to final.png (output of step_upscale_final).
        size_code: '110pc' or '252pc'.
        order_dir: Path to the order output directory.

    Returns:
        Dict with puzzle_surface, tin_lid, puzzle_surface_size, tin_lid_size, size_code.

    Raises:
        ValueError: If size_code is not recognised.
    """
    if size_code not in PRODIGI_SIZES:
        raise ValueError(
            f"Unknown size_code '{size_code}'. Must be one of: {list(PRODIGI_SIZES.keys())}"
        )

    target_w, target_h = PRODIGI_SIZES[size_code]
    order_dir = Path(order_dir)
    order_dir.mkdir(parents=True, exist_ok=True)

    # Load and convert to plain RGB (untagged sRGB — what Prodigi expects)
    img = Image.open(upscaled_path)
    if img.mode != "RGB":
        img = img.convert("RGB")

    src_w, src_h = img.size

    # Scale-to-fill: scale so BOTH axes are >= target, then center-crop
    scale = max(target_w / src_w, target_h / src_h)
    new_w = round(src_w * scale)
    new_h = round(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    left   = (new_w - target_w) // 2
    top    = (new_h - target_h) // 2
    puzzle_surface = img.crop((left, top, left + target_w, top + target_h))

    surface_path = str(order_dir / "puzzle_surface.jpg")
    puzzle_surface.save(
        surface_path,
        format="JPEG",
        quality=95,
        subsampling=0,   # 4:4:4 chroma — maximum colour fidelity for print
        optimize=True,
    )

    # Tin lid: scale-to-fill then center-crop from the already-sized puzzle surface
    lid_w, lid_h = TIN_LID_SIZE
    pw, ph = puzzle_surface.size
    lid_scale = max(lid_w / pw, lid_h / ph)
    lid_new_w = round(pw * lid_scale)
    lid_new_h = round(ph * lid_scale)
    lid_img = puzzle_surface.resize((lid_new_w, lid_new_h), Image.LANCZOS)
    lid_left = (lid_new_w - lid_w) // 2
    lid_top  = (lid_new_h - lid_h) // 2
    tin_lid = lid_img.crop((lid_left, lid_top, lid_left + lid_w, lid_top + lid_h))

    lid_path = str(order_dir / "tin_lid.jpg")
    tin_lid.save(lid_path, format="JPEG", quality=95, subsampling=0, optimize=True)

    print(f"  Export ({size_code}): puzzle_surface {target_w}×{target_h}px, tin_lid {lid_w}×{lid_h}px")

    return {
        "puzzle_surface": surface_path,
        "tin_lid": lid_path,
        "puzzle_surface_size": [target_w, target_h],
        "tin_lid_size": [lid_w, lid_h],
        "size_code": size_code,
    }


def save_manifest(order_dir: str, job_metadata: dict) -> str:
    """Save the final manifest.json with all step results and costs.

    Args:
        order_dir: Path to the order output directory.
        job_metadata: Full job metadata dict (all steps).

    Returns:
        Path to the saved manifest.json.
    """
    manifest_path = Path(order_dir) / "manifest.json"
    manifest = {
        **job_metadata,
        "completed_at": datetime.now().isoformat(),
    }

    # Calculate total cost
    total_cost = 0
    for step_data in manifest.get("steps", {}).values():
        if isinstance(step_data, dict):
            total_cost += step_data.get("cost", 0)
    manifest["total_cost"] = round(total_cost, 3)

    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2, default=str)

    return str(manifest_path)
