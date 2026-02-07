"""
Quality assessment package.

Provides unified quality scoring combining face similarity,
image quality metrics, and resolution checks.

Tuned for animated/cartoon puzzle art (not photorealism):
- Color vibrancy rewards vivid saturated colors
- Edge cleanliness rewards clean cartoon edges
- Sharpness and contrast removed (penalized cartoon art)

Weights are tuned for the no-face-swap cartoon pipeline where face
similarity is typically 0.30–0.42. Visual cartoon quality (vibrancy,
edges, color diversity) carries most of the weight.
"""

from typing import Dict, Optional

from quality.face_similarity import score_face_similarity
from quality.image_quality import assess_image_quality

# Weights for composite score — tuned for cartoon-only pipeline (no face swap)
# Face similarity reduced because cartoon transforms score 0.30–0.42 naturally.
# Visual quality metrics (vibrancy, edges, palette) are the primary signals.
WEIGHTS = {
    "face_similarity": 0.15,            # reduced — cartoon doesn't need exact likeness
    "color_vibrancy": 0.25,             # primary cartoon quality signal
    "face_detection_confidence": 0.10,  # face is present and well-formed
    "resolution": 0.10,                 # mostly binary after upscale
    "edge_cleanliness": 0.20,           # clean cartoon edges, no artifacts
    "color_diversity": 0.20,            # rich scenes with varied palette
}


def assess_quality(
    generated_path: str,
    source_path: Optional[str] = None,
    target_pieces: int = 1000,
    save_thumbnails_dir: Optional[str] = None,
) -> Dict:
    """Unified quality assessment returning a 0-100 composite score.

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
            # Normalize similarity from [-1, 1] to [0, 100]
            raw_sim = face_data.get("similarity", 0.0)
            face_score = max(0, min(100, (raw_sim + 1) * 50))
            # Detection confidence
            face_det_score = face_data.get("generated_det_score", 0.0) * 100

    # Composite score
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
