"""
Main puzzle creation pipeline.

Uses FLUX Kontext Pro backend for AI image transformation.
"""

import argparse
import json
import os
import shutil
from io import BytesIO
from pathlib import Path
from typing import Dict

import requests
from PIL import Image, ImageDraw, ImageOps
from dotenv import load_dotenv

from backends.registry import get_backend, list_backends
from quality.face_similarity import append_metrics, score_face_similarity
from style_presets import STYLE_CHOICES, get_style

load_dotenv()


def add_puzzle_grid(image, grid_size=(8, 8)):
    """Add a simple grid overlay to simulate puzzle pieces."""
    draw = ImageDraw.Draw(image)
    width, height = image.size
    rows, cols = grid_size

    for i in range(1, cols):
        x = i * (width // cols)
        draw.line([(x, 0), (x, height)], fill=(0, 0, 0), width=3)

    for i in range(1, rows):
        y = i * (height // rows)
        draw.line([(0, y), (width, y)], fill=(0, 0, 0), width=3)

    return image


def _download_image(url: str, save_path: str) -> Image.Image:
    """Download an image from a URL and save to disk."""
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content))
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(save_path, quality=95)
    return img


def _prepare_run_directory(input_path: str, style_id: str, backend_name: str) -> Path:
    stem = Path(input_path).stem
    run_dir = Path("output/benchmarks") / stem / f"{style_id}_{backend_name}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _archive_image(src: str, destination_dir: Path, filename: str):
    destination_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, destination_dir / filename)


def create_magical_puzzle(
    input_path: str,
    output_path: str,
    style_id: str,
    subject_description: str,
    backend_name: str = "flux_kontext",
):
    """
    Main pipeline: Load image -> AI transform -> Add puzzle grid -> Save.

    Args:
        input_path: Path to the person's photo.
        output_path: Where to save the final puzzle.
        style_id: Style preset name.
        subject_description: Description of the person(s) in the photo.
        backend_name: Which AI backend to use.
    """
    print(f"Starting puzzle creation...")
    print(f"  Input: {input_path}")
    print(f"  Backend: {backend_name}")
    print(f"  Style: {style_id}")

    # Load and validate image (fix phone rotation via EXIF)
    img = ImageOps.exif_transpose(Image.open(input_path))
    if img.mode != "RGB":
        img = img.convert("RGB")

    max_size = 1024
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))

    temp_path = "output/temp_input.jpg"
    os.makedirs("output", exist_ok=True)
    img.save(temp_path, quality=95)

    backend = get_backend(backend_name)
    style = get_style(style_id)
    run_dir = _prepare_run_directory(input_path, style_id, backend_name)

    metrics_record = {
        "input": input_path,
        "style": style_id,
        "backend": backend_name,
        "subject": subject_description,
    }

    try:
        prompt = style["kontext_prompt"]
        print(f"Generating with {backend.name}...")
        print(f"  Prompt: {prompt[:100]}...")

        result = backend.generate(
            prompt=prompt,
            image_path=temp_path,
            style_settings=style["settings"],
            negative_prompt=style.get("negative_prompt"),
        )

        output_file = str(run_dir / f"output_{style['settings'].get('inference_steps', 30)}steps.png")
        img = _download_image(result.image_url, output_file)
        metrics_record["cost"] = result.cost_estimate

        similarity = score_face_similarity(input_path, output_file)
        if similarity:
            metrics_record["similarity"] = similarity["similarity"]
            metrics_record["similarity_confidence"] = similarity["confidence_level"]
            metrics_record["threshold_flag"] = similarity["threshold_flag"]
            print(f"  Face similarity: {similarity['similarity']:.4f} ({similarity['confidence_level']})")
    except Exception as e:
        print(f"AI transformation failed: {e}")
        print("Continuing with original image...")
        img = Image.open(input_path)

    # Add puzzle grid
    print("Adding puzzle grid...")
    img = add_puzzle_grid(img, grid_size=(8, 8))

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)
    _archive_image(output_path, run_dir, f"puzzle_{style_id}_{backend_name}.png")
    metrics_record["output_path"] = output_path

    append_metrics(run_dir / "similarity_metrics.jsonl", metrics_record)
    print(f"Done! Puzzle saved to {output_path}")
    return output_path


def parse_args():
    all_backends = sorted(list_backends().keys())

    parser = argparse.ArgumentParser(description="Create recognizable character puzzles.")
    parser.add_argument("--input", default="input/Chaz/charlie-outside.jpg", help="Path to source photo")
    parser.add_argument("--output", default="output/magical_puzzle.png", help="Destination for final puzzle")
    parser.add_argument(
        "--style",
        default="storybook_cartoon",
        choices=STYLE_CHOICES,
        help="Preset style to apply",
    )
    parser.add_argument(
        "--subject",
        default="a smiling family member",
        help="Short description of the person(s) in the photo for prompt context",
    )
    parser.add_argument(
        "--backend",
        default="flux_kontext",
        choices=all_backends,
        help="AI generation backend to use",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    create_magical_puzzle(
        input_path=args.input,
        output_path=args.output,
        style_id=args.style,
        subject_description=args.subject,
        backend_name=args.backend,
    )
