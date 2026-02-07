# Active styles — storybook_cartoon, space_explorer, underwater_adventure, pixel_platformer.
# Other styles are shelved (usable for testing via get_style()).
# Each style can set "face_swap": False to auto-disable face swap (pixel art styles).

STYLE_PRESETS = {
    "storybook_cartoon": {
        "kontext_prompt": (
            "Transform this photo into a Pixar-like cartoon illustration. Give the person exaggerated "
            "expressive eyes, soft shading, and a playful costume. Place them in a colorful whimsical "
            "village with floating lanterns, detailed props, and layered depth. Use a warm storybook "
            "illustration style. Keep the person's face, hair, and expression exactly as they are."
        ),
        "negative_prompt": (
            "hyper-realistic, uncanny valley, stiff pose, washed colors, facial distortion, "
            "wrong hair color, changed hairstyle, altered hair texture"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
    },
    "space_explorer": {
        "kontext_prompt": (
            "Transform this photo into a Pixar-like cartoon illustration. Dress the person in a colorful "
            "cartoon astronaut suit with a clear helmet visor showing their face. Place them floating in a "
            "bright, whimsical outer space scene with colorful planets, a rocket ship, friendly cartoon "
            "aliens, glowing nebulas, and twinkling stars. Use vibrant colors, soft cartoon shading, and a "
            "sense of playful wonder. Keep the person's face, hair, and expression exactly as they are."
        ),
        "negative_prompt": (
            "hyper-realistic, dark sci-fi, horror, grim atmosphere, stiff pose, washed colors, "
            "facial distortion, wrong hair color, changed hairstyle, altered hair texture"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
    },
    "underwater_adventure": {
        "kontext_prompt": (
            "Transform this photo into a Pixar-like cartoon illustration. Dress the person in a playful "
            "cartoon diving suit or mermaid costume. Place them in a vibrant underwater scene with colorful "
            "coral reefs, friendly sea creatures like clownfish and turtles, a sunken treasure chest, "
            "flowing kelp, and shimmering bubbles. Use warm turquoise tones with golden light rays filtering "
            "from above, soft cartoon shading, and rich layered depth. Keep the person's face, hair, and "
            "expression exactly as they are."
        ),
        "negative_prompt": (
            "hyper-realistic, dark ocean, murky water, horror, stiff pose, washed colors, "
            "facial distortion, wrong hair color, changed hairstyle, altered hair texture"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
    },
    "pixel_platformer": {
        "kontext_prompt": (
            "Transform this photo into vibrant pixel art in the style of a classic side-scrolling "
            "platformer game. Make the person a cute pixel art character with a recognizable pixelated "
            "version of their face and hair. Place them in a colorful platformer level with pixel "
            "platforms, fluffy clouds, collectible coins and stars, green pipes, and colorful blocks "
            "against a bright blue sky. Use clean pixel art shading with bold, cheerful primary colors "
            "and a playful 16-bit game aesthetic. Keep the person's face, hair, and expression "
            "recognizable in pixel form."
        ),
        "negative_prompt": (
            "photorealistic, blurry, painterly, dark atmosphere, horror, muddy colors, "
            "noisy edges, melted pixels, wrong hair color, changed hairstyle"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
        "face_swap": False,  # pixel art + photorealistic face swap = bad
    },
}

# Shelved styles — not shown in CLI choices but still usable for testing/benchmarks
_SHELVED_STYLES = {
    "fairytale": {
        "kontext_prompt": (
            "Transform this photo into a magical fairytale illustration. Make the person an enchanted "
            "prince or princess wearing an ornate costume with sparkling details. Place them in an "
            "enchanted forest with glowing castle spires, floating lights, and lush flora. Use painterly "
            "rendering with luminous lighting and a shimmering storybook atmosphere. Keep the person's "
            "face, hair, and expression exactly as they are."
        ),
        "negative_prompt": (
            "deformed faces, blurry details, distorted anatomy, modern clothing, photorealistic skin, "
            "extra limbs, wrong hair color, changed hairstyle, altered hair texture"
        ),
        "settings": {"denoising": 0.40, "cfg_scale": 7.0, "inference_steps": 28},
    },
    "superhero": {
        "kontext_prompt": (
            "Transform this photo into a heroic comic-book illustration. Dress the person in sleek "
            "superhero armor with a cape and bold emblem. Place them atop a futuristic skyline at dusk "
            "with dramatic clouds, energy flares, and vibrant neon city lights. Use cinematic rim "
            "lighting and a dynamic pose. Keep the person's face, hair, and expression exactly as they are."
        ),
        "negative_prompt": (
            "casual clothes, weak pose, low contrast, extra fingers, warped faces, grainy rendering, "
            "wrong hair color, changed hairstyle, altered hair texture"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 7.5, "inference_steps": 32},
    },
}

DEFAULT_STYLE = "storybook_cartoon"


def get_style(style_id: str):
    """Get a style config by ID. Checks active styles first, then shelved."""
    key = style_id.lower()
    if key in STYLE_PRESETS:
        return STYLE_PRESETS[key]
    if key in _SHELVED_STYLES:
        return _SHELVED_STYLES[key]
    available = ", ".join(sorted(list(STYLE_PRESETS.keys()) + list(_SHELVED_STYLES.keys())))
    raise ValueError(f"Unknown style '{style_id}'. Available: {available}")


# CLI choices — only active styles
STYLE_CHOICES = sorted(STYLE_PRESETS.keys())
