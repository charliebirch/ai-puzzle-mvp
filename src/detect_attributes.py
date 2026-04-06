"""
Auto-detect person attributes from a photo using Claude vision.

Uses Claude Opus 4.6 with structured output to identify age range, gender,
ethnicity, hair color/style, and skin tone from an uploaded photo. Returns
values that match the dropdown options in wizard_step1_upload.html exactly.

Cost: ~$0.005–0.01 per photo (image tokens + small output).
"""

import base64
import os
from pathlib import Path
from typing import List

from pydantic import BaseModel


# These must match the dropdown options in wizard_step1_upload.html exactly
VALID_AGE_RANGES = ["toddler", "child", "teen", "adult"]
VALID_GENDERS = ["boy", "girl", "person"]
VALID_ETHNICITIES = ["Black", "White", "Asian", "South Asian", "Hispanic/Latino", "Middle Eastern", "Mixed"]
VALID_HAIR_COLORS = ["blonde", "brown", "black", "red", "auburn", "strawberry blonde", "gray", "white"]
VALID_HAIR_STYLES = ["short", "long", "curly", "straight", "wavy", "ponytail", "braids", "bun", "afro", "buzzed"]
VALID_SKIN_TONES = ["very light", "light", "medium", "olive", "brown", "dark brown"]

# quality_grade values — "poor" blocks form submission
VALID_QUALITY_GRADES = ["good", "ok", "poor"]

# Hard-fail phrases that always map to "poor" regardless of model output.
# Keep this list tight — only genuine blockers where the pipeline cannot proceed.
HARD_FAIL_ISSUES = {"no face detected", "face completely hidden", "photo too dark to see", "completely blurry"}


class _DetectedAttributes(BaseModel):
    """Structured output schema for Claude's attribute detection response."""
    age_range: str
    gender: str
    ethnicity: str
    hair_color: str
    hair_style: str
    skin_tone: str
    quality_grade: str       # "good", "ok", or "poor"
    quality_issues: List[str]  # plain-English issues, empty list if none


def detect_attributes(image_path: str) -> dict:
    """Detect person attributes and photo quality from a photo using Claude vision.

    Sends the image to Claude Opus 4.6 with structured output to extract
    age range, gender, ethnicity, hair color, hair style, skin tone, and a
    photo quality assessment.

    quality_grade:
        "good"  — face clearly visible, one person, well-lit, sharp
        "ok"    — usable but has minor issues (slight angle, shadow, etc.)
        "poor"  — cannot proceed (no face, multiple people, face too small/dark)

    Args:
        image_path: Path to the prepared photo (JPEG or PNG).

    Returns:
        Dict with attribute fields plus quality_grade, quality_pass (bool),
        and quality_issues (list of strings). Returns {} on any error.
    """
    try:
        import anthropic
    except ImportError:
        print("  detect_attributes: anthropic package not installed, skipping")
        return {}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  detect_attributes: ANTHROPIC_API_KEY not set, skipping")
        return {}

    try:
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        ext = Path(image_path).suffix.lower()
        media_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(ext, "image/jpeg")

        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.parse(
            model="claude-opus-4-6",
            max_tokens=512,
            system=(
                "You are a photo analyst for a children's puzzle personalisation service. "
                "You assess portrait photos for suitability and detect demographic attributes. "
                "Be accurate but not overly strict — slightly imperfect photos are often still usable."
            ),
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            "Analyse this photo for use in a children's AI puzzle service. "
                            "Be lenient — err strongly toward 'good' or 'ok'. Only use 'poor' for genuine blockers.\n\n"
                            "1. PHOTO QUALITY:\n"
                            "   quality_grade — choose one:\n"
                            "     \"good\": the main subject's face is clearly visible and usable\n"
                            "     \"ok\": usable, with something worth noting (e.g. slight angle, mild shadow, soft focus)\n"
                            "     \"poor\": ONLY use this if the pipeline genuinely cannot proceed — "
                            "i.e. no face is visible at all, or the photo is completely black/unviewable\n\n"
                            "   IMPORTANT rules:\n"
                            "   - Other people in the background are FINE — background gets removed automatically. Do NOT flag this.\n"
                            "   - Sunglasses, hats, or accessories are NOT problems — they will be included in the final image. Do NOT flag these.\n"
                            "   - Slight angles, mild shadows, partial cropping are NOT problems. Do NOT flag these.\n"
                            "   - Only flag genuine hard blockers: no face visible, completely unviewable photo.\n\n"
                            "   quality_issues — list only genuine issues (max 2, empty list if none). "
                            "If the person is wearing accessories, note them informatively not as problems, "
                            "e.g. \"wearing sunglasses — these will appear in the final image\".\n\n"
                            "2. PERSON ATTRIBUTES (for the main foreground subject):\n"
                            f"   age_range — choose one: {VALID_AGE_RANGES}\n"
                            f"   gender — choose one: {VALID_GENDERS} (use 'person' if unclear)\n"
                            f"   ethnicity — choose one or empty string: {VALID_ETHNICITIES}\n"
                            f"   hair_color — choose one or empty string: {VALID_HAIR_COLORS}\n"
                            f"   hair_style — choose one or empty string: {VALID_HAIR_STYLES}\n"
                            f"   skin_tone — choose one or empty string: {VALID_SKIN_TONES}\n\n"
                            "Only return attribute values from the lists above. "
                            "Use empty string for any attribute you cannot confidently determine."
                        )
                    }
                ]
            }],
            output_format=_DetectedAttributes,
        )

        attrs = response.parsed_output

        quality_grade = attrs.quality_grade if attrs.quality_grade in VALID_QUALITY_GRADES else "ok"
        quality_issues = attrs.quality_issues[:3] if attrs.quality_issues else []

        # Escalate to "poor" if any hard-fail phrase appears in issues
        if any(hf in issue.lower() for issue in quality_issues for hf in HARD_FAIL_ISSUES):
            quality_grade = "poor"

        return {
            "age_range": attrs.age_range if attrs.age_range in VALID_AGE_RANGES else "child",
            "gender": attrs.gender if attrs.gender in VALID_GENDERS else "person",
            "ethnicity": attrs.ethnicity if attrs.ethnicity in VALID_ETHNICITIES else "",
            "hair_color": attrs.hair_color if attrs.hair_color in VALID_HAIR_COLORS else "",
            "hair_style": attrs.hair_style if attrs.hair_style in VALID_HAIR_STYLES else "",
            "skin_tone": attrs.skin_tone if attrs.skin_tone in VALID_SKIN_TONES else "",
            "quality_grade": quality_grade,
            "quality_pass": quality_grade != "poor",
            "quality_issues": quality_issues,
        }

    except Exception as e:
        print(f"  detect_attributes: failed — {e}")
        return {}
