"""
PIL compositing helper for Method E.

Removes the white background from a character image and pastes it
onto a scene image with feathered edges. The result is then sent
through Kontext Max for seamless blending.

Used by pipeline_steps.step_composite_all().
"""

import numpy as np
from PIL import Image, ImageFilter


def composite_character_onto_scene(
    character_path: str,
    scene_path: str,
    output_path: str,
) -> str:
    """Composite a white-background character onto a scene image.

    Removes the white background from the character using a numpy threshold,
    feathers the edges with a gaussian blur on the alpha channel, and pastes
    the character centered onto the scene.

    Args:
        character_path: Path to character image (white background).
        scene_path: Path to scene image.
        output_path: Path to save the composite result.

    Returns:
        The output_path for convenience.
    """
    character = Image.open(character_path).convert("RGBA")
    scene = Image.open(scene_path).convert("RGBA")

    # Remove white background via numpy threshold
    char_array = np.array(character)
    # Pixels where R, G, B are all > 240 are considered white background
    white_mask = (
        (char_array[:, :, 0] > 240)
        & (char_array[:, :, 1] > 240)
        & (char_array[:, :, 2] > 240)
    )
    # Set white pixels to transparent
    char_array[white_mask, 3] = 0

    character = Image.fromarray(char_array)

    # Feather edges: blur the alpha channel for smooth blending
    alpha = character.split()[3]
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=2))
    character.putalpha(alpha)

    # Resize character to fit scene (roughly 60% of scene height)
    scene_w, scene_h = scene.size
    char_w, char_h = character.size
    target_h = int(scene_h * 0.6)
    scale = target_h / char_h
    new_w = int(char_w * scale)
    new_h = target_h
    character = character.resize((new_w, new_h), Image.LANCZOS)

    # Center horizontally, place at bottom third
    x = (scene_w - new_w) // 2
    y = scene_h - new_h - int(scene_h * 0.05)  # 5% from bottom

    # Paste character onto scene
    scene.paste(character, (x, y), character)

    # Save as RGB
    result = scene.convert("RGB")
    result.save(output_path, quality=95)

    return output_path
