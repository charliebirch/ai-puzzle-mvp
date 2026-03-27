"""
Quality assessment package.

Two scoring systems:
1. **assess_quality()** — Legacy composite (face similarity + image quality).
   Kept for backward compatibility with existing benchmarks.
2. **score_puzzle_quality()** — New 11-metric puzzle suitability scorer.
   Measures what matters for physical puzzle assembly.
3. **assess_full_quality()** — Runs both: puzzle scorer (primary) + face similarity
   (reported separately, not part of puzzle composite).

The puzzle scorer (from puzzle_scorer.py) is the primary quality gate.
Face similarity is informational only — cartoon transforms naturally score low.
"""

from typing import Dict, Optional

from quality.face_similarity import score_face_similarity
from quality.image_quality import assess_image_quality
from quality.puzzle_scorer import (
    METRIC_DESCRIPTIONS,
    METRIC_WEIGHTS,
    PuzzleGrade,
    PuzzleScore,
    score_puzzle_quality,
)

# Legacy weights for backward-compatible assess_quality()
WEIGHTS = {
    "face_similarity": 0.15,
    "color_vibrancy": 0.25,
    "face_detection_confidence": 0.10,
    "resolution": 0.10,
    "edge_cleanliness": 0.20,
    "color_diversity": 0.20,
}


def assess_quality(
    generated_path: str,
    source_path: Optional[str] = None,
    target_pieces: int = 1000,
    save_thumbnails_dir: Optional[str] = None,
) -> Dict:
    """Legacy quality assessment returning a 0-100 composite score.

    Kept for backward compatibility with benchmarks. New code should use
    assess_full_quality() or score_puzzle_quality() instead.

    Args:
        generated_path: Path to the generated image.
        source_path: Path to the original source photo (for face similarity).
        target_pieces: Target puzzle piece count for resolution scoring.
        save_thumbnails_dir: Optional dir to save face crop thumbnails.

    Returns:
        Dict with individual scores, composite score, and pass/fail status.
    """
    # Image quality metrics
    iq_scores = assess_image_quality(generated_path, target_pieces)

    # Face similarity (if source provided)
    face_score = 0.0
    face_det_score = 0.0
    face_data = None
    if source_path:
        face_data = score_face_similarity(
            source_path, generated_path, save_thumbnails_dir
        )
        if face_data:
            raw_sim = face_data.get("similarity", 0.0)
            face_score = max(0, min(100, (raw_sim + 1) * 50))
            face_det_score = face_data.get("generated_det_score", 0.0) * 100

    composite = (
        WEIGHTS["face_similarity"] * face_score
        + WEIGHTS["color_vibrancy"] * iq_scores["color_vibrancy"]
        + WEIGHTS["face_detection_confidence"] * face_det_score
        + WEIGHTS["resolution"] * iq_scores["resolution"]
        + WEIGHTS["edge_cleanliness"] * iq_scores["edge_cleanliness"]
        + WEIGHTS["color_diversity"] * iq_scores["color_diversity"]
    )

    return {
        "composite_score": round(composite, 1),
        "pass": composite >= 70,
        "face_similarity_raw": face_data.get("similarity", 0.0) if face_data else None,
        "face_similarity_score": round(face_score, 1),
        "face_confidence": face_data.get("confidence_level") if face_data else None,
        "face_detection_confidence": round(face_det_score, 1),
        "color_vibrancy": iq_scores["color_vibrancy"],
        "edge_cleanliness": iq_scores["edge_cleanliness"],
        "color_diversity": iq_scores["color_diversity"],
        "resolution": iq_scores["resolution"],
        "weights": WEIGHTS,
    }


def assess_full_quality(
    generated_path: str,
    source_path: Optional[str] = None,
    puzzle_pieces: int = 1000,
    save_thumbnails_dir: Optional[str] = None,
) -> Dict:
    """Full quality assessment: puzzle scorer (primary) + face similarity (informational).

    The puzzle composite score is the quality gate. Face similarity is reported
    separately since cartoon transforms naturally score 0.30-0.42.

    Args:
        generated_path: Path to the generated image.
        source_path: Path to the original source photo (for face similarity).
        puzzle_pieces: Target puzzle piece count.
        save_thumbnails_dir: Optional dir to save face crop thumbnails.

    Returns:
        Dict with puzzle_score (PuzzleScore), face_similarity data,
        and combined metadata.
    """
    # Primary: puzzle quality scoring (11 metrics, <2s)
    puzzle = score_puzzle_quality(generated_path, puzzle_pieces)

    # Secondary: face similarity (informational, not part of puzzle composite)
    face_data = None
    if source_path:
        try:
            face_data = score_face_similarity(
                source_path, generated_path, save_thumbnails_dir
            )
        except Exception:
            pass  # Face similarity is optional — don't block on failure

    return {
        "puzzle_score": puzzle,
        "puzzle_composite": puzzle.composite,
        "puzzle_grade": puzzle.grade.value,
        "puzzle_pass": puzzle.grade in (PuzzleGrade.PASS,),
        "puzzle_hard_fail": puzzle.grade == PuzzleGrade.HARD_FAIL,
        "hard_fail_reasons": puzzle.hard_fail_reasons,
        "per_metric": {
            name: {
                "raw": m.raw_value,
                "score": m.normalized_score,
                "weight": m.weight,
                "hard_fail": m.hard_fail,
                "description": METRIC_DESCRIPTIONS.get(name, name),
            }
            for name, m in puzzle.per_metric.items()
        },
        "face_similarity_raw": face_data.get("similarity", 0.0) if face_data else None,
        "face_confidence": face_data.get("confidence_level") if face_data else None,
    }
