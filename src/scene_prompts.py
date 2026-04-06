"""
Scene prompt configurations for the 5-step pipeline.

Each scene has prompts for every pipeline step:
- Character generation (Step 2)
- Costume (Step 3)
- Scene generation (Step 4)
- Compositing methods E, K, Q (Step 5)

All prompts are proven through testing — see docs/BEST_PRACTICES.md.

{subject} and {gender_hint} are filled at runtime.
"""

SCENE_CONFIGS = {
    "village": {
        "name": "Magical Village",
        "description": "A whimsical storybook village with cobblestone streets and floating lanterns",

        # Step 2: Character generation (Kontext Max)
        "character_prompt": (
            "Transform this face reference into a full Pixar-like 3D animated character standing "
            "in a fun hero pose. Use this image ONLY as a face and identity reference — do NOT "
            "copy the pose, hands, arms, or body position from the source.\n\n"
            "IDENTITY (preserve exactly):\n"
            "- Skin tone, ethnicity, hair colour, hair texture, hairstyle, face shape\n"
            "- Natural facial proportions — do not enlarge eyes, do not alter jaw or nose\n"
            "- {gender_hint}\n"
            "- This person is {subject}\n\n"
            "POSE (always use this, regardless of source image):\n"
            "- Full standing figure, roughly waist-up visible\n"
            "- Confident, fun hero stance: feet shoulder-width apart, one fist raised triumphantly "
            "or hands on hips, chest forward, slight lean into the viewer\n"
            "- Face directly toward the viewer — face must be fully visible and unobscured\n"
            "- Warm, natural smile\n\n"
            "STYLE:\n"
            "- Pixar 3D animated style, soft cartoon shading, smooth skin\n"
            "- Simple casual clothing, no logos\n"
            "- Plain white background\n"
            "- Clean silhouette edges suitable for compositing"
        ),

        # Gender hints for character prompt
        "gender_hints": {
            "boy": "Natural masculine features",
            "girl": "Soft feminine features, delicate jawline",
            "person": "",
        },

        # Step 3: Costume (Kontext Max)
        "costume_prompt": (
            "Take this animated character and dress them in a whimsical fantasy adventurer "
            "outfit — leather vest, belt with pouches, a small cape, and boots. Keep their "
            "face, skin tone, hair, glasses, and expression exactly the same. Keep the white "
            "background. Same framing and pose."
        ),

        # Step 4: Scene generation (Kontext Max, text-only)
        "scene_prompt": (
            "A vibrant magical storybook village scene with no people or characters. "
            "Ultra-detailed Pixar 3D rendering. Cobblestone streets winding between colorful "
            "crooked houses with flower boxes and thatched roofs. Floating lanterns, a stone "
            "bridge over a sparkling stream, a bakery with a striped awning, a clock tower, "
            "market stalls with colorful fruit. Foreground: scattered leaves, potted "
            "sunflowers, a sleeping cat, a red postbox, a wheelbarrow of flowers. Background: "
            "rolling green hills, a windmill, fluffy clouds, a hot air balloon, birds flying, "
            "a rainbow. Every inch filled with color and detail. Warm golden-hour lighting, "
            "rich saturated colors. No people, no characters, empty scene."
        ),

        # Step 5: Compositing prompts
        "composite_E_prompt": (
            "Make this image look like a single seamless Pixar 3D rendered scene. The animated "
            "character should blend perfectly into the village — match the warm golden-hour "
            "lighting, add natural shadows, smooth all edges. Keep everything exactly as it is, "
            "just make it look unified and natural. Do not change the character's face, skin tone, "
            "hair, or ethnicity. Do not change the village layout."
        ),

        "composite_K_prompt": (
            "Place the animated Pixar character from the first image seamlessly into the "
            "magical village scene from the second image. The character should be standing on "
            "the cobblestone path in the centre of the village, taking up about 40%% of the "
            "image height. Match the warm golden-hour lighting of the scene onto the character. "
            "Add natural ground shadows beneath their feet. The final image should look like a "
            "single unified Pixar 3D rendered scene — no visible compositing artifacts, "
            "seamless edges, consistent lighting throughout. Keep the character exactly as they "
            "are — same face, glasses, beard, hair, costume."
        ),

        "composite_Q_prompt": (
            "Place the animated Pixar character from the first image seamlessly into the "
            "magical village scene from the second image. The character should be standing "
            "further down the cobblestone path in the midground of the scene, appearing at "
            "a natural distance as if they are walking through the village. Match the warm "
            "golden-hour lighting of the scene onto the character. Add natural ground shadows "
            "beneath their feet. The final image should look like a single unified Pixar 3D "
            "rendered scene — no visible compositing artifacts, seamless edges, consistent "
            "lighting throughout. Keep the character exactly as they are — same face, glasses, "
            "beard, hair, costume."
        ),
    },
}

DEFAULT_SCENE = "village"


def get_scene(scene_id: str) -> dict:
    """Get a scene config by ID.

    Args:
        scene_id: Scene identifier (e.g. 'village').

    Returns:
        Scene configuration dict with all prompts.

    Raises:
        ValueError: If scene_id is unknown.
    """
    key = scene_id.lower()
    if key in SCENE_CONFIGS:
        return SCENE_CONFIGS[key]
    available = ", ".join(sorted(SCENE_CONFIGS.keys()))
    raise ValueError(f"Unknown scene '{scene_id}'. Available: {available}")


def get_character_prompt(scene_id: str, subject: str, gender: str = "person") -> str:
    """Build the full character generation prompt with subject and gender hint.

    Args:
        scene_id: Scene identifier.
        subject: Description of the person (e.g. 'a young girl with curly red hair').
        gender: 'boy', 'girl', or 'person'.

    Returns:
        Formatted prompt string ready for Kontext Max.
    """
    scene = get_scene(scene_id)
    gender_hint = scene["gender_hints"].get(gender, "")
    return scene["character_prompt"].format(
        subject=subject,
        gender_hint=gender_hint,
    )


SCENE_CHOICES = sorted(SCENE_CONFIGS.keys())
