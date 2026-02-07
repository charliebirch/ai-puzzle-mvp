from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


def _extract_url(output) -> str:
    """Extract URL from Replicate output, handling multiple return types."""
    if isinstance(output, list):
        output = output[0]
    if isinstance(output, str):
        return output
    if hasattr(output, "url"):
        url_attr = getattr(output, "url")
        return url_attr() if callable(url_attr) else url_attr
    return str(output)


@dataclass
class GenerationResult:
    """Result from a backend generation call."""
    image_url: str
    model_id: str
    cost_estimate: float
    metadata: Dict


class BaseBackend(ABC):
    """Abstract base class for AI generation backends."""

    name: str = "base"
    replicate_id: str = ""
    supports_face_lock: bool = False
    supports_two_step: bool = False
    supports_single_step: bool = True
    cost_per_run: float = 0.0

    @abstractmethod
    def generate(
        self,
        prompt: str,
        image_path: str,
        style_settings: Dict,
        negative_prompt: Optional[str] = None,
        **kwargs,
    ) -> GenerationResult:
        """Generate an image from a prompt and reference photo.

        Args:
            prompt: Text prompt describing desired output.
            image_path: Path to the input/reference image.
            style_settings: Style-specific generation parameters.
            negative_prompt: Things to avoid in generation.
            **kwargs: Backend-specific parameters.

        Returns:
            GenerationResult with the output image URL and metadata.
        """

    def estimate_cost(self, num_steps: int = 1) -> float:
        """Estimate cost for a generation run.

        Args:
            num_steps: Number of generation steps (1 for single-step, 2 for two-step).
        """
        return self.cost_per_run * num_steps

    def get_capabilities(self) -> Dict:
        """Return backend capabilities for the benchmark runner."""
        return {
            "name": self.name,
            "replicate_id": self.replicate_id,
            "supports_face_lock": self.supports_face_lock,
            "supports_two_step": self.supports_two_step,
            "supports_single_step": self.supports_single_step,
            "cost_per_run": self.cost_per_run,
        }
