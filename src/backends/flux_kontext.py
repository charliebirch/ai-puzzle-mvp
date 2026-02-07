import replicate
from typing import Dict, Optional

from backends.base import BaseBackend, GenerationResult, _extract_url


class FluxKontextBackend(BaseBackend):
    """FLUX Kontext Pro - instruction-based image editing that preserves full appearance."""

    name = "flux_kontext"
    replicate_id = "black-forest-labs/flux-kontext-pro:897a70f5a7dbd8a0611413b3b98cf417b45f266bd595c571a22947619d9ae462"
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
        inputs = {
            "input_image": open(image_path, "rb"),
            "prompt": prompt,
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
                "prompt": prompt,
                "aspect_ratio": inputs["aspect_ratio"],
            },
        )
