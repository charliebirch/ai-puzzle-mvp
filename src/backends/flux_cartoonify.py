"""FLUX Kontext Cartoonify — auto-cartoonify without a prompt.

Preserves original composition and applies a cartoon style.
Most "true to photo" option since it can't generate new scenes.
$0.04/run.
"""

import replicate
from typing import Dict, Optional

from backends.base import BaseBackend, GenerationResult, _extract_url


class FluxCartoonifyBackend(BaseBackend):
    """FLUX Cartoonify - no-prompt auto-cartoon conversion."""

    name = "flux_cartoonify"
    replicate_id = "flux-kontext-apps/cartoonify:9aa3d60af1acf308484ead35b0b5be18d7da315e81236ecf0cde09f8e9769843"
    supports_face_lock = False
    supports_single_step = True
    supports_two_step = False
    cost_per_run = 0.04

    def generate(
        self,
        prompt: str,
        image_path: str,
        style_settings: Dict,
        negative_prompt: Optional[str] = None,
        **kwargs,
    ) -> GenerationResult:
        # Cartoonify ignores prompt — it auto-detects and applies cartoon style
        inputs = {
            "input_image": open(image_path, "rb"),
            "aspect_ratio": kwargs.get("aspect_ratio", "4:3"),
            "output_format": "png",
        }

        seed = kwargs.get("seed")
        if seed is not None:
            inputs["seed"] = seed

        output = replicate.run(self.replicate_id, input=inputs)
        image_url = _extract_url(output)

        return GenerationResult(
            image_url=image_url,
            model_id=self.replicate_id,
            cost_estimate=self.cost_per_run,
            metadata={
                "note": "cartoonify — no prompt used",
                "aspect_ratio": inputs["aspect_ratio"],
            },
        )
