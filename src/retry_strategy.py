"""Auto-retry strategy — maps puzzle scoring failures to prompt adjustments.

When a generated image fails quality checks, this module suggests prompt
additions to fix the specific problems detected. Used by fulfill_order.py
in the retry loop.
"""

from typing import Dict, List, Tuple

from quality.puzzle_scorer import PuzzleScore


# Maps metric names to prompt additions that address the failure
METRIC_FIXES: Dict[str, Tuple[float, str]] = {
    # (threshold below which to trigger, prompt addition)
    "flat_region_pct": (
        50,  # trigger when normalized score < 50
        "Add clouds, birds, and atmospheric effects to sky areas. "
        "Add texture, patterns, and small details to all surfaces. "
        "No large flat or uniform color areas anywhere.",
    ),
    "corner_detail_ratio": (
        50,
        "Fill every corner with detail — flowers, butterflies, small animals, "
        "scattered objects, vines, leaves, or decorative elements. "
        "Every edge and corner must have visual interest.",
    ),
    "subject_dominance": (
        50,
        "Make the character very small in the frame, no more than 15% of the image. "
        "Wide panoramic scene with lots of environment detail surrounding the character.",
    ),
    "dominant_color_pct": (
        50,
        "Use a diverse rainbow color palette with many different colors throughout. "
        "Avoid large areas of any single color. Mix warm and cool tones.",
    ),
    "edge_density": (
        50,
        "Add intricate patterns, textures, and fine detail to every surface. "
        "Include architectural details, foliage patterns, and decorative elements.",
    ),
    "color_entropy": (
        50,
        "Use a rich and varied color palette. Include many different colors "
        "and color variations across the entire scene.",
    ),
    "grid_uniformity": (
        50,
        "Distribute visual interest evenly across the entire image. "
        "Every section should have unique colors and details. "
        "No empty or plain areas anywhere.",
    ),
    "hue_diversity": (
        50,
        "Include objects in many different colors — red, blue, green, yellow, "
        "purple, orange, pink. Use the full rainbow spectrum.",
    ),
    "gradient_magnitude": (
        50,
        "Add surface textures and patterns — wood grain, stone texture, "
        "fabric patterns, leaf veins, cobblestone detail.",
    ),
}


def get_retry_prompt_additions(puzzle_score: PuzzleScore) -> List[str]:
    """Get prompt additions to fix quality issues.

    Examines each metric in the puzzle score and returns prompt additions
    for any metric scoring below its threshold.

    Args:
        puzzle_score: The PuzzleScore from the previous attempt.

    Returns:
        List of prompt addition strings. Empty if no fixes needed.
    """
    additions = []

    for metric_name, (threshold, prompt_addition) in METRIC_FIXES.items():
        metric = puzzle_score.per_metric.get(metric_name)
        if metric and metric.normalized_score < threshold:
            additions.append(prompt_addition)

    return additions


def build_retry_prompt(original_prompt: str, puzzle_score: PuzzleScore) -> str:
    """Build an adjusted prompt incorporating fixes for quality failures.

    Args:
        original_prompt: The original generation prompt.
        puzzle_score: The PuzzleScore from the previous attempt.

    Returns:
        Adjusted prompt with fixes appended. Returns original if no fixes needed.
    """
    additions = get_retry_prompt_additions(puzzle_score)
    if not additions:
        return original_prompt

    # Combine unique additions (avoid duplicates if metrics overlap)
    combined = " ".join(additions)

    # Append to original prompt
    return f"{original_prompt} {combined}"


def estimate_retry_cost(
    base_cost: float,
    max_attempts: int,
) -> float:
    """Estimate maximum cost for retries.

    Args:
        base_cost: Cost per generation attempt (e.g., $0.04 for Kontext Pro).
        max_attempts: Maximum number of attempts.

    Returns:
        Maximum total cost if all attempts are used.
    """
    return base_cost * max_attempts
