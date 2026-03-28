"""Structured subject description builder.

Builds a natural-language subject description from structured fields
(age, gender, hair, skin tone, etc.) for use in generation prompts.
Also includes auto-detection of skin tone from the source photo.
"""

from typing import Optional

import cv2
import numpy as np


# Valid options for each field
AGE_RANGES = ["toddler", "child", "teen", "adult"]
GENDERS = ["boy", "girl", "person"]
ETHNICITIES = ["", "Black", "White", "Asian", "South Asian", "Hispanic/Latino", "Middle Eastern", "Mixed"]
HAIR_COLORS = ["blonde", "brown", "black", "red", "gray", "white", "auburn", "strawberry blonde"]
HAIR_STYLES = ["short", "long", "curly", "straight", "ponytail", "braids", "buzzed", "wavy", "bun", "afro"]
SKIN_TONES = ["very light", "light", "medium", "olive", "brown", "dark brown"]


def build_subject_description(
    age_range: str = "child",
    gender: str = "person",
    ethnicity: str = "",
    hair_color: str = "",
    hair_style: str = "",
    skin_tone: str = "",
    extras: str = "",
) -> str:
    """Build a natural subject description from structured fields.

    Ethnicity and skin tone are critical for identity preservation —
    the AI model will alter these if not explicitly stated in the prompt.

    Args:
        age_range: One of AGE_RANGES (toddler/child/teen/adult).
        gender: One of GENDERS (boy/girl/person).
        ethnicity: Ethnicity (e.g., "Black", "Asian"). Important for identity.
        hair_color: Hair color (e.g., "blonde", "brown").
        hair_style: Hair style (e.g., "short", "curly", "afro").
        skin_tone: Skin tone description (e.g., "light", "dark brown").
        extras: Freetext additional features (e.g., "freckles, glasses").

    Returns:
        Natural language description like "a young Black boy with afro black hair,
        dark brown skin, freckles".
    """
    # Build base: "a young Black boy" or "a teen Asian girl"
    base = f"a {age_range}"
    if ethnicity:
        base += f" {ethnicity}"
    base += f" {gender}"
    parts = [base]

    # Skin tone — always include if available (critical for identity)
    if skin_tone:
        parts.append(f"{skin_tone} skin")

    # Hair description
    hair_parts = []
    if hair_style:
        hair_parts.append(hair_style)
    if hair_color:
        hair_parts.append(hair_color)
    if hair_parts:
        parts.append(f"{' '.join(hair_parts)} hair")

    # Extras
    if extras and extras.strip():
        parts.append(extras.strip())

    return ", ".join(parts)


def detect_skin_tone(image_path: str) -> Optional[str]:
    """Auto-detect skin tone from a photo using face detection + LAB color space.

    Uses OpenCV Haar cascade to find the face, samples forehead pixels,
    converts to LAB, and maps L channel to a skin tone label.

    Args:
        image_path: Path to the photo.

    Returns:
        Skin tone label (e.g., "light", "medium") or None if no face detected.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Load Haar cascade for face detection (ships with OpenCV)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

    if len(faces) == 0:
        return None

    # Use the largest face
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

    # Sample forehead region (top 30% of face, middle 60% width)
    # This avoids eyebrows, eyes, and facial hair
    forehead_y1 = y + int(h * 0.05)
    forehead_y2 = y + int(h * 0.30)
    forehead_x1 = x + int(w * 0.20)
    forehead_x2 = x + int(w * 0.80)

    # Clamp to image bounds
    forehead_y1 = max(0, forehead_y1)
    forehead_y2 = min(img.shape[0], forehead_y2)
    forehead_x1 = max(0, forehead_x1)
    forehead_x2 = min(img.shape[1], forehead_x2)

    forehead = img[forehead_y1:forehead_y2, forehead_x1:forehead_x2]

    if forehead.size == 0:
        return None

    # Convert to LAB and get mean L value
    lab = cv2.cvtColor(forehead, cv2.COLOR_BGR2LAB)
    mean_l = float(np.mean(lab[:, :, 0]))

    # Map L value to skin tone label
    # LAB L channel: 0 (black) to 255 (white) in OpenCV's uint8 representation
    if mean_l >= 210:
        return "very light"
    elif mean_l >= 185:
        return "light"
    elif mean_l >= 160:
        return "medium"
    elif mean_l >= 135:
        return "olive"
    elif mean_l >= 105:
        return "brown"
    else:
        return "dark brown"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build subject description or detect skin tone.")
    parser.add_argument("--photo", help="Photo for skin tone detection")
    parser.add_argument("--age", default="child", choices=AGE_RANGES)
    parser.add_argument("--gender", default="person", choices=GENDERS)
    parser.add_argument("--hair-color", default="")
    parser.add_argument("--hair-style", default="")
    parser.add_argument("--skin-tone", default="")
    parser.add_argument("--extras", default="")
    args = parser.parse_args()

    if args.photo:
        detected = detect_skin_tone(args.photo)
        print(f"Detected skin tone: {detected or 'could not detect'}")
        if detected and not args.skin_tone:
            args.skin_tone = detected

    desc = build_subject_description(
        age_range=args.age,
        gender=args.gender,
        hair_color=args.hair_color,
        hair_style=args.hair_style,
        skin_tone=args.skin_tone,
        extras=args.extras,
    )
    print(f"Subject description: {desc}")
