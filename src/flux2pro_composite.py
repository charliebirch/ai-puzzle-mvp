"""
FLUX 2 Pro two-image compositing for Methods K and Q.

Sends a character image and a scene image as two input_images
to FLUX 2 Pro, which composites them based on the prompt.

Cost: ~$0.08 per run.
"""

import time
from io import BytesIO
from pathlib import Path

import replicate
import requests
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

REPLICATE_MODEL = "black-forest-labs/flux-2-pro"
COST_PER_RUN = 0.08


def run_flux2pro_composite(
    character_path: str,
    scene_path: str,
    prompt: str,
    output_path: str,
    seed: int = None,
) -> dict:
    """Composite a character into a scene using FLUX 2 Pro's two-image input.

    Args:
        character_path: Path to the costumed character image.
        scene_path: Path to the empty scene image.
        prompt: Compositing prompt describing how to place the character.
        output_path: Path to save the result.
        seed: Optional seed for reproducibility.

    Returns:
        dict with output_path, cost, elapsed_seconds, and size.
    """
    start = time.time()

    with open(character_path, "rb") as f1, open(scene_path, "rb") as f2:
        inputs = {
            "prompt": prompt,
            "input_images": [f1, f2],
            "resolution": "4 MP",
            "aspect_ratio": "1:1",
            "output_format": "png",
            "output_quality": 100,
            "safety_tolerance": 5,
        }
        if seed is not None:
            inputs["seed"] = seed

        output = replicate.run(REPLICATE_MODEL, input=inputs)

    # Extract URL from output
    image_url = output
    if isinstance(output, list):
        image_url = output[0]
    if hasattr(image_url, "url"):
        image_url = str(getattr(image_url, "url"))
    image_url = str(image_url)

    # Download and save
    response = requests.get(image_url, timeout=120)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content))
    img.save(output_path, quality=100)

    elapsed = time.time() - start

    return {
        "output_path": output_path,
        "cost": COST_PER_RUN,
        "elapsed_seconds": round(elapsed, 1),
        "size": list(img.size),
    }
