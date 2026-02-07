"""Face swap post-processing utility for face+hair preservation.

Uses codeplugtech/face-swap (simple, fast, ~$0.003/run).
"""

import replicate
from dataclasses import dataclass
from typing import Dict

from backends.base import _extract_url


@dataclass
class SwapResult:
    """Result from a face swap operation."""
    image_url: str
    model_id: str
    cost_estimate: float
    metadata: Dict


def face_swap(
    swap_image_path: str,
    target_image_path: str,
    gender: str = "male",
    hair_source: str = "swap",
    upscale: bool = True,
) -> SwapResult:
    """Swap face from the original photo onto a stylized image.

    Args:
        swap_image_path: Path to original customer photo (source face).
        target_image_path: Path to the stylized/generated image.
        gender: Kept for API compatibility (unused by this model).
        hair_source: Kept for API compatibility (unused by this model).
        upscale: Kept for API compatibility (unused by this model).

    Returns:
        SwapResult with the swapped image URL and metadata.
    """
    model_id = "codeplugtech/face-swap:278a81e7ebb22db98bcba54de985d22cc1abeead2754eb1f2af717247be69b34"
    cost = 0.003

    inputs = {
        "swap_image": open(swap_image_path, "rb"),
        "input_image": open(target_image_path, "rb"),
    }

    output = replicate.run(model_id, input=inputs)
    image_url = _extract_url(output)

    return SwapResult(
        image_url=image_url,
        model_id=model_id,
        cost_estimate=cost,
        metadata={
            "gender": gender,
            "hair_source": hair_source,
        },
    )
