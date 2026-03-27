# Two-tier style system: Art Style (animation vs cartoon) x Scene (village, space, underwater).
#
# Animation styles: single-step Kontext Pro — transforms photo into animated character + scene.
# Cartoon styles: two-step Cartoonify → Kontext Pro — cartoon filter first, then scene placement.
#
# All styles disable face swap (face_swap: False) — it makes images too photorealistic.
#
# {subject} placeholder — replaced at runtime with a description of the person in the photo.
# This should be specific: "a 5-year-old boy with curly red hair, freckles, and green eyes".
# The model uses this alongside the image reference to maintain the right features.
#
# negative_prompt was removed from all active styles — FLUX Kontext Pro/Max does NOT accept
# negative_prompt as an API input. It was dead code being passed to generate() but never sent
# to Replicate. Negative concepts are now worked into the positive prompt instead.
# Shelved styles still have negative_prompt for reference but it's not used.
#
# Old styles (storybook_cartoon, space_explorer, etc.) are in _SHELVED_STYLES for CLI testing.

STYLE_PRESETS = {
    # --- Animation (single-step Kontext Pro) ---
    #
    # Prompt design rules for puzzle-quality output:
    # 1. Character must be TINY (10-15% of frame) — say "very small", "distant", "far away"
    # 2. Wide-angle panoramic framing — say "wide-angle", "zoomed out", "bird's-eye"
    # 3. Fill EVERY corner with named objects — sky has clouds/birds, ground has flowers/stones
    # 4. 3 depth layers: foreground objects, midground scene, background sky/mountains
    # 5. List 15+ specific objects to force the model to fill the frame
    #
    # NOTE: Village produces inconsistent character quality — Kontext doesn't force a
    # costume change so characters often look half-real/distorted. Space and underwater
    # are more reliable. Village will be revisited with better prompt tuning.
    "animation_village": {
        "pipeline": "kontext",
        "kontext_prompt": (
            "Turn {subject} into a tiny 3D Pixar-style cartoon character, very small and "
            "far away in the scene, only about 10 percent of the image. "
            "Keep their face shape, skin tone, hair color, and hairstyle the same. "
            "Ultra wide-angle panoramic view of a magical storybook village. "
            "Foreground: cobblestone path with scattered leaves, a wooden cart full of "
            "pumpkins, a sleeping cat, potted sunflowers, a red postbox. "
            "Midground: crooked colorful houses with flower boxes, a bakery with a striped "
            "awning, a clock tower, a stone bridge over a stream, market stalls with fruit. "
            "Background: rolling green hills, windmill, fluffy clouds, hot air balloon, "
            "birds flying, rainbow. Every inch filled with color and detail. "
            "Pixar 3D cartoon shading, warm golden-hour lighting, rich saturated colors."
        ),
        "face_swap": False,
    },
    "animation_space": {
        "pipeline": "kontext",
        "kontext_prompt": (
            "Turn {subject} into a tiny 3D Pixar-style cartoon character in a colorful "
            "spacesuit with a clear bubble helmet, very small and floating in the scene, "
            "only about 10 percent of the image. "
            "Keep their face shape, skin tone, hair color, and hairstyle the same. "
            "Ultra wide-angle panoramic view of a bright whimsical outer space scene. "
            "Top-left: a ringed planet with colorful bands. Top-right: a pink and purple "
            "nebula cloud with twinkling stars. Bottom-left: a red retro rocket ship with "
            "round windows. Bottom-right: a friendly green alien waving from a small moon. "
            "Scattered throughout: an asteroid belt, a space station, a comet with a "
            "glowing tail, a satellite dish, a UFO, a constellation pattern, floating "
            "space crystals, a telescope, a lunar rover. Every corner filled with objects. "
            "Pixar 3D cartoon shading, bright vivid colors against deep blue-purple space."
        ),
        "face_swap": False,
    },
    "animation_underwater": {
        "pipeline": "kontext",
        "kontext_prompt": (
            "Turn {subject} into a tiny 3D Pixar-style cartoon character in a cartoon "
            "diving suit with goggles, very small and swimming in the scene, only about "
            "10 percent of the image. "
            "Keep their face shape, skin tone, hair color, and hairstyle the same. "
            "Ultra wide-angle panoramic view of a vibrant underwater ocean scene. "
            "Top area: shimmering water surface with golden sun rays filtering through, "
            "a school of yellow fish, floating jellyfish. "
            "Left side: tall pink and orange coral reef tower, a sea turtle, an anchor. "
            "Right side: a sunken pirate ship with barnacles, a friendly octopus, starfish "
            "on rocks. Bottom: sandy ocean floor with seashells, a treasure chest spilling "
            "gold coins, sea urchins, anemones, hermit crabs. "
            "Scattered: tropical fish in every color, bubbles, kelp forests, a seahorse, "
            "a manta ray, a clownfish in an anemone. Every corner filled with sea life. "
            "Pixar 3D cartoon shading, warm turquoise-to-teal gradient lighting."
        ),
        "face_swap": False,
    },

    # --- Cartoon (two-step: Cartoonify → Kontext Pro scene placement) ---
    "cartoon_village": {
        "pipeline": "cartoonify_then_kontext",
        "kontext_prompt": (
            "Keep this cartoon character's face, skin tone, and hair exactly as they are. "
            "Make them very small and far away in the scene, only about 10 percent of the image. "
            "Ultra wide-angle panoramic view of a magical storybook village. "
            "Foreground: cobblestone path with fallen leaves, a wheelbarrow of flowers, "
            "a friendly dog, scattered stepping stones, mushrooms growing by a tree stump. "
            "Midground: colorful crooked houses with thatched roofs, a candy shop, a "
            "wishing well, a stone fountain with a fish, laundry hanging between buildings. "
            "Background: mountains with snow peaks, a castle on a distant hill, birds, "
            "fluffy clouds, a crescent moon starting to rise. "
            "Every inch filled with color and detail. Warm storybook lighting. "
            "Do not make it more realistic. Keep the cartoon style."
        ),
        "face_swap": False,
    },
    "cartoon_space": {
        "pipeline": "cartoonify_then_kontext",
        "kontext_prompt": (
            "Keep this cartoon character's face, skin tone, and hair exactly as they are. "
            "Put them in a colorful spacesuit with a clear bubble helmet. "
            "Make them very small and floating in the scene, only about 10 percent of the image. "
            "Ultra wide-angle panoramic view of a bright whimsical outer space scene. "
            "Top-left: a giant ringed planet. Top-right: a glowing nebula in pink and gold. "
            "Bottom-left: a retro rocket with flames. Bottom-right: a moon base with a dome. "
            "Scattered: friendly aliens, a comet, an asteroid belt, a space station, "
            "constellations, floating crystals, a satellite, twinkling stars everywhere. "
            "Every corner filled with objects. Bright vivid colors. "
            "Do not make it more realistic. Keep the cartoon style."
        ),
        "face_swap": False,
    },
    "cartoon_underwater": {
        "pipeline": "cartoonify_then_kontext",
        "kontext_prompt": (
            "Keep this cartoon character's face, skin tone, and hair exactly as they are. "
            "Put them in a cartoon diving suit with goggles. "
            "Make them very small and swimming in the scene, only about 10 percent of the image. "
            "Ultra wide-angle panoramic view of a vibrant underwater ocean world. "
            "Top: shimmering surface with sun rays, jellyfish, a school of fish. "
            "Left: towering coral reef in pink and orange, a sea turtle, a seahorse. "
            "Right: a sunken ship covered in barnacles, a playful octopus, starfish. "
            "Bottom: sandy floor with seashells, a treasure chest, sea urchins, crabs. "
            "Scattered: tropical fish in every color, bubbles, kelp, a manta ray, "
            "a clownfish, an eel peeking from a cave. Every corner filled with sea life. "
            "Warm turquoise lighting. Do not make it more realistic. Keep the cartoon style."
        ),
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
