"""
Scene prompt configurations for the 5-step pipeline.

Prompts are stored as plain text files in prompts/<scene>/ for easy
editing and copy-pasting into the parallel testing system.

Each scene has prompts for every pipeline step:
- Character generation (Step 2)    → prompts/<scene>/character.txt
- Costume (Step 3)                 → prompts/<scene>/costume_*.txt
- Scene generation (Step 4)        → prompts/<scene>/scene.txt
- Compositing (Step 5)             → prompts/<scene>/composite.txt

Placeholders like {subject} and {gender_hint} are filled at runtime.
"""

from pathlib import Path

# Prompt files live alongside src/ in the project root
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(scene_id: str, filename: str) -> str:
    """Load a prompt text file from prompts/<scene>/<filename>.

    Returns the file contents with trailing whitespace stripped.
    Raises FileNotFoundError if the prompt file doesn't exist.
    """
    path = _PROMPTS_DIR / scene_id / filename
    return path.read_text().strip()


SCENE_CONFIGS = {
    "village": {
        "name": "Magical Village",
        "description": "A whimsical storybook village with cobblestone streets and floating lanterns",

        # Gender hints for character prompt — substituted into {gender_hint}
        "gender_hints": {
            "boy": "Natural masculine features",
            "girl": "Soft feminine features, delicate jawline",
            "person": "",
        },

        # Outfit choices shown in the wizard wardrobe picker (Step 3).
        # Each prompt is loaded from prompts/village/costume_<id>.txt
        "outfit_choices": [
            {
                "id": "adventurer",
                "name": "The Adventurer",
                "emoji": "\u2694\ufe0f",
                "description": "Leather vest, belt with pouches, swirling cape & boots",
            },
            {
                "id": "wizard",
                "name": "The Wizard",
                "emoji": "\U0001f9d9",
                "description": "Flowing star robes, tall pointed hat & a glowing staff",
            },
        ],
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


def _pick_character_variant(age_range: str, gender: str) -> str:
    """Pick the right character prompt filename based on age and gender.

    Routing:
        toddler (any gender)  → character_toddler.txt
        child   (any gender)  → character_child.txt
        teen/adult + boy      → character_boy.txt
        teen/adult + girl     → character_girl.txt
        anything else         → character.txt (neutral fallback)
    """
    if age_range in ("toddler",):
        return "character_toddler.txt"
    if age_range in ("child",):
        return "character_child.txt"
    if gender in ("boy", "girl"):
        return f"character_{gender}.txt"
    return "character.txt"


def get_character_prompt(
    scene_id: str,
    subject: str,
    gender: str = "person",
    age_range: str = "adult",
) -> str:
    """Build the full character generation prompt for the given age and gender.

    Routes to the appropriate prompt file:
        toddler → character_toddler.txt  (max cute, chubby, no gendered build)
        child   → character_child.txt    (kid proportions, no gendered build)
        teen/adult + boy  → character_boy.txt   (masculine proportions)
        teen/adult + girl → character_girl.txt   (feminine proportions)
        fallback          → character.txt        (neutral)

    Each file is self-contained with age/gender-appropriate PROPORTIONS,
    IDENTITY hints, and POSE baked in. Only {subject} is substituted.

    Args:
        scene_id: Scene identifier.
        subject: Description of the person (e.g. 'the person in the input image').
        gender: 'boy', 'girl', or 'person'. Used for teen/adult routing.
        age_range: 'toddler', 'child', 'teen', or 'adult'. Overrides gender
            for young children (toddler/child always use neutral body).

    Returns:
        Formatted prompt string ready for Kontext Max.
    """
    filename = _pick_character_variant(age_range, gender)
    try:
        prompt = _load_prompt(scene_id, filename)
    except FileNotFoundError:
        prompt = _load_prompt(scene_id, "character.txt")
    return prompt.format(subject=subject)


def get_costume_prompt(scene_id: str, subject: str, outfit_id: str = None) -> str:
    """Build the costume prompt with subject description substituted in.

    Loads from prompts/<scene>/costume_<outfit_id>.txt if an outfit is
    specified, otherwise falls back to costume_default.txt.

    Args:
        scene_id: Scene identifier.
        subject: Full subject description. Used as an explicit text anchor
            so the model doesn't alter hair/identity.
        outfit_id: Optional outfit choice ID (e.g. 'adventurer', 'wizard').

    Returns:
        Formatted prompt string ready for Kontext Max.
    """
    filename = f"costume_{outfit_id}.txt" if outfit_id else "costume_default.txt"
    try:
        prompt = _load_prompt(scene_id, filename)
    except FileNotFoundError:
        prompt = _load_prompt(scene_id, "costume_default.txt")
    return prompt.format(subject=subject)


def get_scene_prompt(scene_id: str) -> str:
    """Load the scene generation prompt (text-only, no image).

    Args:
        scene_id: Scene identifier.

    Returns:
        Prompt string for FLUX 2 Pro scene generation.
    """
    return _load_prompt(scene_id, "scene.txt")


def get_composite_prompt(scene_id: str) -> str:
    """Load the compositing prompt for Method E.

    Args:
        scene_id: Scene identifier.

    Returns:
        Prompt string for Kontext Max compositing.
    """
    return _load_prompt(scene_id, "composite.txt")


SCENE_CHOICES = sorted(SCENE_CONFIGS.keys())
