"""FLUX Kontext Max — premium version of Kontext Pro.

Higher quality generation at $0.08/run (2x Pro price).
May preserve identity better natively due to more inference steps.
"""

from typing import Dict, Optional

from backends.base import BaseBackend, GenerationResult, _extract_url
from replicate_retry import run_with_retry


class FluxKontextMaxBackend(BaseBackend):
    """FLUX Kontext Max - premium instruction-based image editing."""

    name = "flux_kontext_max"
    replicate_id = "black-forest-labs/flux-kontext-max:8389ed8e4b16016c44fcdcc3ad142cf1e182e0a1ecaf0347b3e5254303f2beac"
    supports_face_lock = False
    supports_single_step = True
    supports_two_step = False
    cost_per_run = 0.08

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

        # Pass through optional Replicate params if provided
        if "safety_tolerance" in kwargs:
            inputs["safety_tolerance"] = kwargs["safety_tolerance"]
        if "prompt_upsampling" in kwargs:
            inputs["prompt_upsampling"] = kwargs["prompt_upsampling"]

        output = run_with_retry(self.replicate_id, input=inputs)
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
