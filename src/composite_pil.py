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

    # Remove white background via numpy threshold.
    # Use >230 (more aggressive than >240) to catch near-white edge pixels
    # that would otherwise remain as a whitish halo.
    char_array = np.array(character)
    white_mask = (
        (char_array[:, :, 0] > 230)
        & (char_array[:, :, 1] > 230)
        & (char_array[:, :, 2] > 230)
    )
    char_array[white_mask, 3] = 0

    character = Image.fromarray(char_array)

    # Feather edges with a larger blur so Kontext Max has softer boundaries
    # to blend — radius=5 vs the old radius=2 gives noticeably softer edges.
    alpha = character.split()[3]
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=5))
    character.putalpha(alpha)

    # Resize character to fit scene (roughly 60% of scene height).
    # In landscape (4:3) this keeps the character as the clear focal point.
    scene_w, scene_h = scene.size
    char_w, char_h = character.size
    target_h = int(scene_h * 0.6)
    scale = target_h / char_h
    new_w = int(char_w * scale)
    new_h = target_h
    character = character.resize((new_w, new_h), Image.LANCZOS)

    # Place character left-of-centre for landscape composition:
    # centre point at ~38% from left, leaving the right ~60% as visible scene.
    # This gives a natural "character in foreground, village behind" look.
    x = int(scene_w * 0.38) - new_w // 2
    y = scene_h - new_h - int(scene_h * 0.05)  # 5% from bottom

    # Pre-fill near-white character areas with scene colours before pasting.
    # Without this, semi-transparent character edge pixels keep their whitish RGB
    # values — when Kontext Max has a bad seed, those white-RGB pixels at partial
    # alpha produce a visible cream halo. Replacing them with scene colours means
    # even a bad seed blends gracefully (scene colour over scene = no halo).
    char_arr = np.array(character)
    scene_arr = np.array(scene)

    # Clamp paste position to scene bounds
    paste_x = max(0, x)
    paste_y = max(0, y)
    paste_x2 = min(scene_w, x + new_w)
    paste_y2 = min(scene_h, y + new_h)

    # Corresponding slice within the character array
    char_x_start = paste_x - x
    char_y_start = paste_y - y
    char_x_end = char_x_start + (paste_x2 - paste_x)
    char_y_end = char_y_start + (paste_y2 - paste_y)

    char_slice = char_arr[char_y_start:char_y_end, char_x_start:char_x_end]
    scene_slice = scene_arr[paste_y:paste_y2, paste_x:paste_x2]

    # Near-white character pixels (all RGB channels > 215, alpha < 200)
    # are replaced with the underlying scene colour so there is no white to leak.
    near_white = (
        (char_slice[:, :, 0] > 215)
        & (char_slice[:, :, 1] > 215)
        & (char_slice[:, :, 2] > 215)
        & (char_slice[:, :, 3] < 200)
    )
    char_slice[near_white, 0] = scene_slice[near_white, 0]
    char_slice[near_white, 1] = scene_slice[near_white, 1]
    char_slice[near_white, 2] = scene_slice[near_white, 2]

    char_arr[char_y_start:char_y_end, char_x_start:char_x_end] = char_slice

    # Apply a vertical gradient fade across the bottom 15% of the character.
    # The feet region has the hardest white→character transition. By fading the
    # alpha to 0 at the very bottom edge, we give Kontext Max a smooth gradient
    # to blend rather than a hard cut, which significantly reduces the chance of
    # a visible white strip at ground level.
    fade_rows = int(new_h * 0.15)
    if fade_rows > 0:
        gradient = np.linspace(1.0, 0.0, fade_rows)  # 1.0 at top → 0.0 at bottom
        alpha_channel = char_arr[:, :, 3].astype(np.float32)
        for i, factor in enumerate(gradient):
            row_idx = new_h - fade_rows + i
            if 0 <= row_idx < new_h:
                alpha_channel[row_idx, :] *= factor
        char_arr[:, :, 3] = np.clip(alpha_channel, 0, 255).astype(np.uint8)

    character = Image.fromarray(char_arr)

    # Paste character onto scene
    scene.paste(character, (x, y), character)

    # Save as RGB
    result = scene.convert("RGB")
    result.save(output_path, quality=95)

    return output_path
