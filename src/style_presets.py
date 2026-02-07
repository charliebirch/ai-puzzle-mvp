# Two-tier style system: Art Style (animation vs cartoon) x Scene (village, space, underwater).
#
# Animation styles: single-step Kontext Pro — transforms photo into animated character + scene.
# Cartoon styles: two-step Cartoonify → Kontext Pro — cartoon filter first, then scene placement.
#
# All styles disable face swap (face_swap: False) — it makes images too photorealistic.
#
# Old styles (storybook_cartoon, space_explorer, etc.) are in _SHELVED_STYLES for CLI testing.

STYLE_PRESETS = {
    # --- Animation (single-step Kontext Pro) ---
    "animation_village": {
        "pipeline": "kontext",
        "kontext_prompt": (
            "Create a stunning Pixar-quality animated character inspired by this person's general "
            "appearance. Give them exaggerated cartoon proportions — big expressive eyes, a playful "
            "smile, and a dynamic adventurous pose. Dress them in a whimsical fantasy outfit. Place "
            "them in a vibrant magical village with floating lanterns, cobblestone streets, and lush "
            "gardens. Rich color palette, dramatic cartoon lighting, cinematic composition."
        ),
        "negative_prompt": (
            "hyper-realistic, uncanny valley, stiff pose, washed colors, facial distortion, "
            "wrong hair color, changed hairstyle, altered hair texture"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
        "face_swap": False,
    },
    "animation_space": {
        "pipeline": "kontext",
        "kontext_prompt": (
            "Create a stunning Pixar-quality animated character inspired by this person's general "
            "appearance. Give them exaggerated cartoon proportions — big expressive eyes, a look of "
            "amazement, and a dynamic weightless pose. Dress them in a colourful puffy cartoon "
            "astronaut suit with a clear bubble helmet. Place them floating in bright whimsical outer "
            "space with colorful planets, a rocket ship, friendly cartoon aliens, glowing nebulas, "
            "and twinkling stars. Rich color palette, dramatic cartoon lighting, cinematic composition."
        ),
        "negative_prompt": (
            "hyper-realistic, dark sci-fi, horror, grim atmosphere, stiff pose, washed colors, "
            "facial distortion, wrong hair color, changed hairstyle, altered hair texture"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
        "face_swap": False,
    },
    "animation_underwater": {
        "pipeline": "kontext",
        "kontext_prompt": (
            "Create a stunning Pixar-quality animated character inspired by this person's general "
            "appearance. Give them exaggerated cartoon proportions — big expressive eyes, a joyful "
            "grin, and a dynamic swimming pose. Dress them in a whimsical cartoon diving suit with "
            "goggles. Place them in a vibrant underwater world with colorful coral reefs, friendly "
            "sea creatures, a glowing sunken treasure chest, flowing kelp, and shimmering bubbles. "
            "Warm turquoise tones with golden light rays from above. Rich color palette, dramatic "
            "cartoon lighting, cinematic composition."
        ),
        "negative_prompt": (
            "hyper-realistic, dark ocean, murky water, horror, stiff pose, washed colors, "
            "facial distortion, wrong hair color, changed hairstyle, altered hair texture"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
        "face_swap": False,
    },

    # --- Cartoon (two-step: Cartoonify → Kontext Pro scene placement) ---
    "cartoon_village": {
        "pipeline": "cartoonify_then_kontext",
        "kontext_prompt": (
            "Place this cartoon character in a vibrant magical village with floating lanterns, "
            "cobblestone streets, and lush gardens. Give them a whimsical fantasy outfit and a dynamic "
            "adventurous pose. Warm storybook lighting, cinematic composition. Keep the cartoon art "
            "style exactly as it is — do not make it more realistic."
        ),
        "negative_prompt": (
            "photorealistic, hyper-realistic, uncanny valley, stiff pose, washed colors"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
        "face_swap": False,
    },
    "cartoon_space": {
        "pipeline": "cartoonify_then_kontext",
        "kontext_prompt": (
            "Place this cartoon character floating in bright whimsical outer space. Give them a "
            "colourful puffy astronaut suit with a clear bubble helmet and a weightless pose. Colorful "
            "planets, a rocket ship, friendly cartoon aliens, glowing nebulas, twinkling stars. "
            "Cinematic composition. Keep the cartoon art style exactly as it is — do not make it "
            "more realistic."
        ),
        "negative_prompt": (
            "photorealistic, hyper-realistic, dark sci-fi, horror, grim atmosphere, stiff pose"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
        "face_swap": False,
    },
    "cartoon_underwater": {
        "pipeline": "cartoonify_then_kontext",
        "kontext_prompt": (
            "Place this cartoon character swimming in a vibrant underwater world. Give them a cartoon "
            "diving suit with goggles and a dynamic swimming pose. Colorful coral reefs, friendly sea "
            "creatures, a glowing treasure chest, flowing kelp, shimmering bubbles. Warm turquoise "
            "tones with golden light from above. Keep the cartoon art style exactly as it is — do not "
            "make it more realistic."
        ),
        "negative_prompt": (
            "photorealistic, hyper-realistic, dark ocean, murky water, horror, stiff pose"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
        "face_swap": False,
    },
}

# Shelved styles — not shown in web UI but still usable for CLI testing/benchmarks
_SHELVED_STYLES = {
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
        "face_swap": False,
    },
    "storybook_identity": {
        "kontext_prompt": (
            "Transform this photo into a Pixar-like 3D animated character. The character MUST have "
            "the same face shape, eye color, nose shape, mouth, and facial features as the person "
            "in the photo. Maintain their exact hairstyle and hair color. Place them in a colorful "
            "whimsical village with floating lanterns and layered depth. Soft cartoon shading, warm "
            "storybook lighting."
        ),
        "negative_prompt": (
            "hyper-realistic, uncanny valley, stiff pose, washed colors, facial distortion, "
            "wrong hair color, changed hairstyle, altered hair texture"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
        "pulid_settings": {"id_weight": 1.0, "start_step": 0},
    },
    "storybook_stylized": {
        "kontext_prompt": (
            "Create a stunning Pixar-quality animated character inspired by this person's general "
            "appearance. Give them exaggerated cartoon proportions — big expressive eyes, a playful "
            "smile, and a dynamic adventurous pose. Dress them in a whimsical fantasy outfit. Place "
            "them in a vibrant magical village with floating lanterns, cobblestone streets, and lush "
            "gardens. Rich color palette, dramatic cartoon lighting, cinematic composition."
        ),
        "negative_prompt": (
            "hyper-realistic, uncanny valley, stiff pose, washed colors, facial distortion, "
            "wrong hair color, changed hairstyle, altered hair texture"
        ),
        "settings": {"denoising": 0.45, "cfg_scale": 6.8, "inference_steps": 30},
        "pulid_settings": {"id_weight": 0.5, "start_step": 4},
    },
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

DEFAULT_STYLE = "animation_village"


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
