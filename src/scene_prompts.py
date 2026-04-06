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
            "Transform this face reference into a full Pixar-like 3D animated character in a "
            "dynamic adventurous pose. Use this image ONLY as a face and identity reference — "
            "do NOT copy the pose, hands, arms, or body position from the source.\n\n"
            "ANATOMY (strict — always apply):\n"
            "- Standard human anatomy: exactly two eyes, two ears, one nose, one mouth\n"
            "- The source image may have imperfect background removal leaving blobs or bumps "
            "near the edges — these are background artifacts, NOT features of the person. "
            "Ignore all background shapes and generate only correct human anatomy.\n\n"
            "PROPORTIONS (critical — this is the Pixar cartoon look):\n"
            "- Oversized cartoon head: the head is approximately ONE THIRD of the character's "
            "total visible height — this large-head proportion is essential to the style\n"
            "- Compact, stocky body: roughly 2.5 to 3 heads tall total, NOT a realistic human "
            "height. Short legs, wide chest, no elongated limbs\n"
            "- Chunky oversized cartoon hands and forearms\n"
            "- Slight low camera angle — the viewer is looking slightly upward at the character, "
            "giving a dynamic heroic lean-forward perspective\n\n"
            "IDENTITY (preserve exactly):\n"
            "- Skin tone, ethnicity, hair colour, hair texture, hairstyle, face shape\n"
            "- Expressive cartoon eyes that feel alive, while faithfully preserving this "
            "person's actual ethnicity, skin tone, and facial structure\n"
            "- {gender_hint}\n"
            "- This person is {subject}\n\n"
            "POSE (always use this, regardless of source image):\n"
            "- Full figure visible from feet (or near feet) to top of head\n"
            "- Dynamic leaning-forward pose: body angled toward viewer, arms out mid-motion, "
            "weight on one foot, full of energy and excitement — like a hero charging into adventure\n"
            "- Face turned toward the viewer — face must be fully visible and unobscured\n"
            "- Huge open joyful grin with visible teeth, eyebrows raised in delight\n\n"
            "STYLE:\n"
            "- Pixar 3D animated style, rich cartoon shading, smooth skin with warm subsurface "
            "scattering, dramatic cartoon lighting with warm highlights and cool shadows\n"
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
        # Default prompt used if no outfit is selected.
        # {subject} is substituted at runtime with the full subject description,
        # giving the model an explicit text anchor for hair colour, texture, and style.
        "costume_prompt": (
            "Take this animated character and dress them in a whimsical fantasy adventurer "
            "outfit — leather vest, belt with pouches, a small cape, and boots. "
            "This character is {subject}. "
            "Keep their face, skin tone, hair colour, hair texture, and hairstyle exactly "
            "as they are — do not alter the hair in any way. Keep glasses and expression "
            "exactly the same. Keep the white background. Same framing and pose."
        ),

        # Selectable outfit choices shown in the wizard wardrobe picker.
        # Each entry: id, name, emoji, description, prompt.
        # All prompts use {subject} for explicit hair/identity anchoring at runtime.
        "outfit_choices": [
            {
                "id": "adventurer",
                "name": "The Adventurer",
                "emoji": "⚔️",
                "description": "Leather vest, belt with pouches, swirling cape & boots",
                "prompt": (
                    "Take this animated character and dress them in a whimsical fantasy adventurer "
                    "outfit — a worn leather vest over a linen shirt, a wide belt with pouches and "
                    "a small dagger, a dramatic swirling cape, and sturdy adventurer boots. "
                    "This character is {subject}. "
                    "Keep their face, skin tone, hair colour, hair texture, and hairstyle exactly "
                    "as they are — do not alter the hair in any way. Keep glasses and expression "
                    "exactly the same. Keep the white background. Same framing and pose."
                ),
            },
            {
                "id": "wizard",
                "name": "The Wizard",
                "emoji": "🧙",
                "description": "Flowing star robes, tall pointed hat & a glowing staff",
                "prompt": (
                    "Take this animated character and dress them in a magnificent wizard outfit — "
                    "long flowing deep-purple robes covered in golden stars and moons, a tall "
                    "pointed wizard hat with a curled brim, and they are holding a gnarled wooden "
                    "staff with a glowing blue gem at the top. "
                    "This character is {subject}. "
                    "Keep their face, skin tone, hair colour, hair texture, and hairstyle exactly "
                    "as they are — the wizard hat sits on top of their existing hair, it does not "
                    "replace or hide it. Do not alter the hair in any way. Keep glasses and "
                    "expression exactly the same. Keep the white background. Same framing and pose."
                ),
            },
        ],

        # Step 4: Scene generation (FLUX 2 Pro, text-only)
        # Landscape 4:3 composition — wide cobblestone street stretching left to right,
        # character will be composited left-of-centre, scene fills the right two thirds.
        "scene_prompt": (
            "A vibrant magical storybook village scene with absolutely no people or characters. "
            "WIDE LANDSCAPE PANORAMIC composition — the village street stretches horizontally "
            "across the full width of the image. Pixar 3D rendered, cinematic quality. "
            "Every surface has texture, wear, or pattern — no large areas of uniform colour.\n\n"
            "FOREGROUND (bottom third) — a wide cobblestone path running left to right:\n"
            "Worn cobblestones with moss growing between stones across the full width, scattered "
            "autumn leaves, a puddle reflecting the lanterns, a plain red postbox with no text, "
            "a wheelbarrow overflowing with orange and purple flowers on the left side, a wicker "
            "basket of apples in the centre, a weathered wooden signpost with blank arrow-shaped "
            "boards (no writing), stacked clay pots and barrels on the right side, scattered "
            "petals across the path.\n\n"
            "MIDGROUND — the village heart stretching across the width:\n"
            "Colourful crooked houses lining both sides of the street with warm glowing windows "
            "(curtains and flower pots visible on inside sills), thatched roofs with varied "
            "colours and wear. A stone bridge arching over a sparkling stream — the stream "
            "reflects sunlight, gentle ripples, lily pads, fish shadow. "
            "LEFT SIDE: a bakery with plain red-and-white striped awning (no text) and bread "
            "loaves in window, a sleeping tabby cat curled on a doorstep. "
            "RIGHT SIDE: A tall clock tower with a large ornate face showing crisp Roman numerals "
            "only, market stalls with colourful fruit, hanging lanterns, bolts of fabric — stall "
            "canopies have plain stripes, no writing. Floating golden lanterns throughout.\n\n"
            "BACKGROUND (top third) — sky and distance with rich colour:\n"
            "Sky must show MULTIPLE colours: vivid cornflower blue and lavender-purple at top, "
            "fading through coral and pink toward the horizon, golden light rays breaking through "
            "layered cloud formations. The blue and purple must be clearly visible, not washed out. "
            "A windmill on a rolling green hill in the distance centre-right. A hot air balloon "
            "with colourful stripes of red, blue, yellow, and green. A rainbow arcing across the "
            "wide sky. Distant birds in flight. Fluffy cumulus clouds with warm-lit edges and "
            "distinctly cool blue-purple shadow undersides. The stream reflects cool blue sky.\n\n"
            "CORNER DETAIL (critical — must have distinct objects in every corner):\n"
            "Top-left: a gnarled oak tree branch with hanging lanterns extending inward. "
            "Top-right: the clock tower upper section with weather vane. "
            "Bottom-left: a pot of sunflowers beside the bakery step. "
            "Bottom-right: stacked barrels and a string of colourful bunting flags.\n\n"
            "Warm golden-hour lighting. Rich saturated colour palette spanning reds, oranges, "
            "yellows, greens, blues, purples, and pinks. No people, no characters, empty scene.\n\n"
            "CRITICAL — NO TEXT: No text, words, letters, or writing anywhere in the image. "
            "All shop fronts, awnings, signs, boards, and surfaces must be plain, patterned, "
            "or decorative only. The only exception is the clock face which uses crisp Roman "
            "numerals. Any other text or lettering is strictly forbidden."
        ),

        # Step 5: Compositing prompts
        "composite_E_prompt": (
            "Make this image look like a single seamless Pixar 3D rendered scene — a cinematic "
            "frame straight from a Pixar feature film. The animated character is standing on the "
            "left side of the wide village street; the scene stretches to the right behind them. "
            "The character should feel like they were always part of the village: match the warm "
            "golden-hour lighting on their skin, add a soft natural ground shadow beneath their "
            "feet, smooth all edges so there is no visible seam between character and scene.\n\n"
            "IMPORTANT — PRESERVE SCENE DETAIL:\n"
            "Keep ALL background detail exactly as it is — do not alter, blur, simplify, or "
            "fade any buildings, textures, window details, market stalls, or objects in the "
            "scene. The sky gradient, cloud formations, and light rays must remain unchanged. "
            "The cobblestone textures, moss, puddle reflection, and scattered objects at ground "
            "level must stay fully visible around the character's feet.\n\n"
            "Corner elements must be preserved in full detail: the tree branch with lanterns "
            "(top-left), the clock tower (top-right), the sunflowers (bottom-left), the stacked "
            "barrels and bunting (bottom-right).\n\n"
            "GROUND BLEND: Replace any white, grey, or washed-out area around the character's "
            "feet and legs with the cobblestone ground texture — the character must stand "
            "directly on the cobblestones with no background colour showing.\n\n"
            "Rich saturated colour palette, dramatic cartoon lighting with warm highlights and "
            "soft cool shadows, cinematic depth and atmosphere. Keep the character's face, "
            "skin tone, hair, and ethnicity exactly as they are. "
            "Do not add any text, words, letters, or writing anywhere in the image."
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


def get_costume_prompt(scene_id: str, subject: str, outfit_id: str = None) -> str:
    """Build the costume prompt with subject description substituted in.

    Args:
        scene_id: Scene identifier.
        subject: Full subject description (e.g. 'a young man with short dark hair').
            Used as an explicit text anchor so the model doesn't alter hair/identity.
        outfit_id: Optional outfit choice ID. Falls back to scene default if not found.

    Returns:
        Formatted prompt string ready for Kontext Max.
    """
    scene = get_scene(scene_id)
    prompt = scene["costume_prompt"]
    if outfit_id:
        for choice in scene.get("outfit_choices", []):
            if choice["id"] == outfit_id:
                prompt = choice["prompt"]
                break
    return prompt.format(subject=subject)


SCENE_CHOICES = sorted(SCENE_CONFIGS.keys())
