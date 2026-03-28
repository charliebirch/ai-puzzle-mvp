# Style presets for AI Puzzle character generation.
#
# Three scenes: village, space, underwater. All single-step Kontext Pro.
# Character fills the frame with themed costume and full Pixar transformation.
#
# {subject} placeholder — replaced at runtime with a description of the person.
# e.g. "a young boy with curly red hair and freckles"

STYLE_PRESETS = {
    "village": {
        "pipeline": "kontext",
        "kontext_prompt": (
            "Create a stunning Pixar-quality animated character inspired by {subject}'s general "
            "appearance. Give them exaggerated cartoon proportions — big expressive eyes, a playful "
            "smile, and a dynamic adventurous pose. Dress them in a whimsical fantasy outfit. Place "
            "them in a vibrant magical village with floating lanterns, cobblestone streets, and lush "
            "gardens. Rich color palette, dramatic cartoon lighting, cinematic composition."
        ),
        "face_swap": False,
    },
    "space": {
        "pipeline": "kontext",
        "kontext_prompt": (
            "Transform {subject} into a Pixar-like cartoon illustration. Dress them in a colorful "
            "cartoon astronaut suit with a clear helmet visor showing their face. Place them floating "
            "in a bright, whimsical outer space scene with colorful planets, a rocket ship, friendly "
            "cartoon aliens, glowing nebulas, and twinkling stars. Use vibrant colors, soft cartoon "
            "shading, and a sense of playful wonder. Keep their face, hair, and expression exactly "
            "as they are."
        ),
        "face_swap": False,
    },
    "underwater": {
        "pipeline": "kontext",
        "kontext_prompt": (
            "Transform {subject} into a Pixar-like cartoon illustration. Dress them in a playful "
            "cartoon diving suit or mermaid costume. Place them in a vibrant underwater scene with "
            "colorful coral reefs, friendly sea creatures like clownfish and turtles, a sunken "
            "treasure chest, flowing kelp, and shimmering bubbles. Use warm turquoise tones with "
            "golden light rays filtering from above, soft cartoon shading, and rich layered depth. "
            "Keep their face, hair, and expression exactly as they are."
        ),
        "face_swap": False,
    },
}

DEFAULT_STYLE = "village"


def get_style(style_id: str):
    """Get a style config by ID."""
    key = style_id.lower()
    if key in STYLE_PRESETS:
        return STYLE_PRESETS[key]
    available = ", ".join(sorted(STYLE_PRESETS.keys()))
    raise ValueError(f"Unknown style '{style_id}'. Available: {available}")


STYLE_CHOICES = sorted(STYLE_PRESETS.keys())
