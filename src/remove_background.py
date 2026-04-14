"""
Background removal via Replicate.

Removes the background from a photo and replaces it with white,
so the AI model can focus entirely on the person.

Cost: ~$0.01/run on Replicate.
"""

import os
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# Recraft — preserves hair edge quality and fine detail
REPLICATE_MODEL = "recraft-ai/recraft-remove-background"
COST_PER_RUN = 0.01


def _extract_url(output) -> str:
    """Extract URL from Replicate output."""
    if isinstance(output, list):
        output = output[0]
    if isinstance(output, str):
        return output
    if hasattr(output, "url"):
        return str(getattr(output, "url"))
    return str(output)


def remove_background(input_path: str, output_path: str) -> dict:
    """Remove background from a photo and replace with white.

    Args:
        input_path: Path to input photo
        output_path: Path to save the result (PNG with white background)

    Returns:
        dict with status, cost, and output path
    """
    print(f"Removing background from {input_path}...")

    from replicate_retry import run_with_retry

    with open(input_path, "rb") as f:
        output = run_with_retry(
            REPLICATE_MODEL,
            input={"image": f},
        )

    image_url = _extract_url(output)
    response = requests.get(image_url, timeout=120)
    response.raise_for_status()

    # The model returns a PNG with transparent background
    # Composite onto white background
    fg = Image.open(BytesIO(response.content)).convert("RGBA")
    white_bg = Image.new("RGBA", fg.size, (255, 255, 255, 255))
    result = Image.alpha_composite(white_bg, fg).convert("RGB")
    result.save(output_path, quality=95)

    print(f"  Background removed: {result.size[0]}x{result.size[1]} -> {output_path}")

    return {
        "status": "ok",
        "cost_estimate": COST_PER_RUN,
        "output_path": output_path,
        "size": list(result.size),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python src/remove_background.py input.jpg output.png")
        sys.exit(1)
    result = remove_background(sys.argv[1], sys.argv[2])
    print(f"Done. Cost: ${result['cost_estimate']}")
