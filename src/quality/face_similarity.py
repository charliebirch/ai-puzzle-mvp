"""
Face similarity scoring using InsightFace (ArcFace 512-dim embeddings).

Thresholds:
    >0.6  - High confidence same person
    >0.5  - Likely same person
    0.3-0.5 - Uncertain
    <0.3  - Different person
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

# InsightFace is lazy-loaded to avoid import errors if not installed
_app = None


def _get_face_app():
    """Lazy-initialize InsightFace app (downloads model on first use)."""
    global _app
    if _app is None:
        from insightface.app import FaceAnalysis
        _app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        _app.prepare(ctx_id=0, det_size=(640, 640))
    return _app


@dataclass
class FaceDetection:
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    embedding: np.ndarray  # 512-dim ArcFace embedding
    score: float  # detection confidence
    crop: Optional[np.ndarray] = None  # cropped face image (BGR)


def _detect_faces(image_path: str) -> List[FaceDetection]:
    """Detect faces and extract ArcFace embeddings."""
    image = cv2.imread(image_path)
    if image is None:
        return []

    app = _get_face_app()
    faces = app.get(image)

    results = []
    for face in faces:
        x1, y1, x2, y2 = [int(v) for v in face.bbox]
        # Clamp to image bounds
        h, w = image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        crop = image[y1:y2, x1:x2].copy() if (x2 > x1 and y2 > y1) else None

        results.append(FaceDetection(
            bbox=(x1, y1, x2, y2),
            embedding=face.normed_embedding,
            score=float(face.det_score),
            crop=crop,
        ))

    # Sort by detection confidence descending
    results.sort(key=lambda f: f.score, reverse=True)
    return results


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two normalized embedding vectors."""
    return float(np.dot(a, b))


def save_face_thumbnails(
    source_path: str,
    generated_path: str,
    output_dir: str,
) -> dict:
    """Save cropped face thumbnails for visual inspection."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    saved = {}
    for label, path in [("source", source_path), ("generated", generated_path)]:
        faces = _detect_faces(path)
        if faces and faces[0].crop is not None:
            thumb_path = output / f"face_{label}.jpg"
            # Resize crop to consistent thumbnail size
            crop = cv2.resize(faces[0].crop, (128, 128))
            cv2.imwrite(str(thumb_path), crop)
            saved[label] = str(thumb_path)

    return saved


def score_face_similarity(
    source_path: str,
    generated_path: str,
    save_thumbnails_dir: Optional[str] = None,
) -> Optional[dict]:
    """Score facial identity similarity between source and generated images.

    Uses InsightFace ArcFace 512-dim embeddings for proper identity comparison.

    Returns:
        Dict with similarity score and metadata, or None if faces not detected.
    """
    source_faces = _detect_faces(source_path)
    generated_faces = _detect_faces(generated_path)

    if not source_faces or not generated_faces:
        return {
            "similarity": 0.0,
            "source_detected": len(source_faces),
            "generated_detected": len(generated_faces),
            "threshold_flag": True,
            "confidence_level": "no_face_detected",
        }

    # Compare best face from each image
    source = source_faces[0]
    generated = generated_faces[0]
    similarity = _cosine_similarity(source.embedding, generated.embedding)

    # Confidence level based on thresholds
    if similarity > 0.6:
        confidence = "high"
    elif similarity > 0.5:
        confidence = "likely"
    elif similarity > 0.3:
        confidence = "uncertain"
    else:
        confidence = "different_person"

    result = {
        "similarity": round(similarity, 4),
        "source_bbox": source.bbox,
        "generated_bbox": generated.bbox,
        "source_det_score": round(source.score, 4),
        "generated_det_score": round(generated.score, 4),
        "source_faces_count": len(source_faces),
        "generated_faces_count": len(generated_faces),
        "threshold_flag": similarity < 0.5,
        "confidence_level": confidence,
    }

    if save_thumbnails_dir:
        thumbs = save_face_thumbnails(source_path, generated_path, save_thumbnails_dir)
        result["thumbnails"] = thumbs

    return result


def append_metrics(metrics_path: Path, record: dict):
    """Append a metrics record to a JSONL file."""
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with metrics_path.open("a") as f:
        # Convert numpy values for JSON serialization
        clean = {}
        for k, v in record.items():
            if isinstance(v, np.floating):
                clean[k] = float(v)
            elif isinstance(v, np.integer):
                clean[k] = int(v)
            elif isinstance(v, np.ndarray):
                clean[k] = v.tolist()
            else:
                clean[k] = v
        f.write(json.dumps(clean) + "\n")
